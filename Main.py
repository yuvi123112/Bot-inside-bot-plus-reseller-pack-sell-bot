import os
import asyncio
import discord
from discord.ext import commands
from capmonster_python import HCaptchaTask
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import random
import string
import time
import requests
import json

TOKEN = "MTM2MzQ0MzE1OTAwNjMxNDY2OA.GvCZMH.u0VnJEI-NPDlwvF7c4NFlCLnoix96vrZdpSzHg"
CAPMONSTER_KEY = "3fdf7e4881366ecd820f6f48686f4bc8"
MAILTM_API_URL = "https://api.mail.tm"
MAILTM_USER = "dhimanritu85@chefalicious.com"
MAILTM_PASSWORD = "Atlasos@1234"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="$", intents=intents)

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Create an authentication token to use the mail.tm API
def get_mailtm_auth_token():
    response = requests.post(f"{MAILTM_API_URL}/token", json={"address": MAILTM_USER, "password": MAILTM_PASSWORD})
    if response.status_code == 200:
        data = response.json()
        return data['token']
    else:
        print("Error: Unable to authenticate with mail.tm.")
        return None

# Function to create a temporary email using mail.tm API
def create_temp_email():
    token = get_mailtm_auth_token()
    if not token:
        return None

    headers = {
        'Authorization': f'Bearer {token}'
    }

    # Request to create a new temporary email address
    response = requests.post(f"{MAILTM_API_URL}/emails", headers=headers)
    if response.status_code == 201:
        data = response.json()
        temp_email = data['address']
        print(f"Temporary Email Created: {temp_email}")
        return temp_email
    else:
        print("Error: Unable to create temporary email.")
        return None

# Function to check the inbox for a verification email
def check_inbox(temp_email):
    token = get_mailtm_auth_token()
    if not token:
        return None
    
    headers = {
        'Authorization': f'Bearer {token}'
    }

    # Get the email ID by checking inbox
    response = requests.get(f"{MAILTM_API_URL}/emails/{temp_email}", headers=headers)
    if response.status_code == 200:
        data = response.json()
        for email in data['hydra:member']:
            if "discord.com" in email['from']:  # Check for Discord verification email
                print(f"Found email from Discord: {email['subject']}")
                verification_link = extract_verification_link(email['text'])
                if verification_link:
                    return verification_link
        print("No verification email found.")
        return None
    else:
        print("Error: Unable to retrieve inbox.")
        return None

# Extract the verification link from the email body (Discord's verification email format)
def extract_verification_link(body):
    import re
    match = re.search(r"https?://[^\s]+", body)
    if match:
        return match.group(0)
    return None

# Function to create a Discord account
async def create_account():
    # 1. Create a temporary email
    temp_email = create_temp_email()
    if not temp_email:
        return None, None, None
    
    # 2. Use the first 8 characters of the temporary email (before @) as the username
    username = temp_email.split('@')[0][:8]  # First 8 characters before '@'
    
    password = generate_random_string(12)

    capmonster = HCaptchaTask(CAPMONSTER_KEY)
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)

    driver.get("https://discord.com/register")
    time.sleep(5)

    driver.find_element(By.NAME, "email").send_keys(temp_email)
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, '//div[@class="css-19bb58m"]').click()
    time.sleep(1)

    # Solve the captcha
    site_key = "f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34"
    task_id = capmonster.create_task("https://discord.com/register", site_key)
    result = capmonster.join_task_result(task_id)

    driver.execute_script("""document.querySelector('[name="h-captcha-response"]').innerHTML = arguments[0];""", result['gRecaptchaResponse'])
    driver.execute_script("document.querySelector('form').submit()")

    time.sleep(15)  # Wait for Discord to process and possibly send a verification email
    driver.quit()

    # Check the inbox for verification email
    verification_link = check_inbox(temp_email)
    if verification_link:
        # Open the verification link
        driver = uc.Chrome(options=options)
        driver.get(verification_link)
        time.sleep(5)  # Allow time for the page to load
        driver.quit()

        # Return the email, username, and password (or token if available)
        return temp_email, username, password
    else:
        print("Verification failed.")
        return None, None, None

@bot.command()
async def caccnt(ctx, num: int):
    await ctx.reply(f"Creating {num} accounts. Please wait...")

    tokens = []
    for _ in range(num):
        try:
            email, username, password = await create_account()
            if email and username and password:
                tokens.append(f"Email: {email}\nUsername: {username}\nPassword: {password}")
            else:
                tokens.append("Error: Account creation or verification failed.")
        except Exception as e:
            tokens.append(f"Error: {str(e)}")

    # Send tokens to the user via DM
    for t in tokens:
        await ctx.author.send(t)

bot.run(TOKEN)
