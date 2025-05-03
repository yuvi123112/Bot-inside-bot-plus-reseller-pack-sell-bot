import os
import asyncio
import discord
from discord.ext import commands

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import random
import string
import time
import requests
import json
from capmonstercloudclient import CapMonsterClient
from capmonstercloudclient.requests import HCaptchaTaskRequest

TOKEN = "MTM2MzQ0MzE1OTAwNjMxNDY2OA.GvCZMH.u0VnJEI-NPDlwvF7c4NFlCLnoix96vrZdpSzHg"
CAPMONSTER_KEY = "3fdf7e4881366ecd820f6f48686f4bc8"
MAILTM_API_URL = "https://api.mail.tm"
MAILTM_USER = "dhimanritu85@chefalicious.com"
MAILTM_PASSWORD = "Atlasos@1234"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="$", intents=intents)

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_mailtm_auth_token():
    response = requests.post(f"{MAILTM_API_URL}/token", json={"address": MAILTM_USER, "password": MAILTM_PASSWORD})
    if response.status_code == 200:
        data = response.json()
        return data['token']
    else:
        print("Error: Unable to authenticate with mail.tm.")
        return None

def create_temp_email():
    token = get_mailtm_auth_token()
    if not token:
        return None

    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.get(f"{MAILTM_API_URL}/me", headers=headers)
    if response.status_code == 200:
        data = response.json()
        temp_email = data['address']
        print(f"Temporary Email Ready: {temp_email}")
        return temp_email
    else:
        print("Error: Unable to fetch existing mail.tm email.")
        return None

def check_inbox():
    token = get_mailtm_auth_token()
    if not token:
        return None

    headers = {
        'Authorization': f'Bearer {token}'
    }

    response = requests.get(f"{MAILTM_API_URL}/messages", headers=headers)
    if response.status_code == 200:
        data = response.json()
        for email in data['hydra:member']:
            if "discord.com" in email['from']['address']:
                print(f"Found email from Discord: {email['subject']}")
                email_detail = requests.get(f"{MAILTM_API_URL}/messages/{email['id']}", headers=headers).json()
                verification_link = extract_verification_link(email_detail['text'])
                return verification_link
    return None

def extract_verification_link(body):
    import re
    match = re.search(r"https?://[^\s]+", body)
    return match.group(0) if match else None

async def create_account():
    temp_email = create_temp_email()
    if not temp_email:
        return None, None, None

    username = temp_email.split('@')[0][:8]
    password = generate_random_string(12)

    client = CapMonsterClient(CAPMONSTER_KEY)
    task = HCaptchaTaskRequest(website_url="https://discord.com/register", website_key="f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34")
    task_id = client.create_task(task)
    result = client.join_task_result(task_id)

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

    driver.execute_script("""document.querySelector('[name="h-captcha-response"]').innerHTML = arguments[0];""", result.solution.gRecaptchaResponse)
    driver.execute_script("document.querySelector('form').submit()")
    time.sleep(15)
    driver.quit()

    verification_link = check_inbox()
    if verification_link:
        driver = uc.Chrome(options=options)
        driver.get(verification_link)
        time.sleep(5)
        driver.quit()
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

    for t in tokens:
        await ctx.author.send(t)

bot.run(TOKEN)
