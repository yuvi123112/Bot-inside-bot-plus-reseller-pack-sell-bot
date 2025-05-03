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
import re

from capmonstercloud.client import Client as CapmonsterClient
from capmonstercloud.tasks import HCaptchaTask

TOKEN = "MTM2MzQ0MzE1OTAwNjMxNDY2OA.GvCZMH.u0VnJEI-NPDlwvF7c4NFlCLnoix96vrZdpSzHg"
CAPMONSTER_KEY = "3fdf7e4881366ecd820f6f48686f4bc8"
MAILTM_API_URL = "https://api.mail.tm"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="$", intents=intents)

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Register a new mail.tm account and get token
def register_mailtm():
    username = f"{generate_random_string(8)}@chefalicious.com"
    password = generate_random_string(12)
    res = requests.post(f"{MAILTM_API_URL}/accounts", json={"address": username, "password": password})
    if res.status_code == 201:
        token_res = requests.post(f"{MAILTM_API_URL}/token", json={"address": username, "password": password})
        if token_res.status_code == 200:
            token = token_res.json()['token']
            return username, password, token
    print("Mail.tm registration failed.")
    return None, None, None

# Check for Discord verification email and extract link
def check_inbox(auth_token):
    headers = {'Authorization': f'Bearer {auth_token}'}
    for _ in range(30):  # Wait for up to ~60 seconds
        res = requests.get(f"{MAILTM_API_URL}/messages", headers=headers)
        if res.status_code == 200:
            data = res.json()
            for msg in data['hydra:member']:
                if "discord" in msg.get("from", {}).get("address", ""):
                    msg_id = msg['id']
                    msg_data = requests.get(f"{MAILTM_API_URL}/messages/{msg_id}", headers=headers).json()
                    match = re.search(r'https:\/\/click\.discord\.com\/[^\s"]+', msg_data.get("text", ""))
                    if match:
                        return match.group(0)
        time.sleep(2)
    return None

# Solve captcha using CapMonster
async def solve_captcha():
    client = CapmonsterClient(CAPMONSTER_KEY)
    task = HCaptchaTask(
        website_url="https://discord.com/register",
        website_key="f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34"
    )
    task_id = await client.create_task(task)
    result = await client.join_task_result(task_id)
    return result.solution.gRecaptchaResponse

# Create a Discord account
async def create_account():
    email, mail_password, mail_token = register_mailtm()
    if not email:
        return None

    password = generate_random_string()
    username = email.split('@')[0]

    # Set up Chrome
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)

    driver.get("https://discord.com/register")
    time.sleep(5)

    driver.find_element(By.NAME, "email").send_keys(email)
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)

    # Fill birthday
    driver.find_element(By.XPATH, '//select[@aria-label="Month"]').send_keys("May")
    driver.find_element(By.XPATH, '//select[@aria-label="Day"]').send_keys("10")
    driver.find_element(By.XPATH, '//select[@aria-label="Year"]').send_keys("2000")

    time.sleep(1)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()

    time.sleep(5)

    # Solve captcha
    token = await solve_captcha()
    driver.execute_script(f'document.querySelector("[name=h-captcha-response]").innerHTML="{token}";')
    driver.execute_script("document.querySelector('form').submit();")

    time.sleep(10)

    # Try to get token from local storage
    try:
        local_token = driver.execute_script("return window.localStorage.getItem('token');")
        if local_token:
            local_token = json.loads(local_token)
        else:
            local_token = "Token not found."
    except:
        local_token = "Error retrieving token."

    # Check for verification email
    link = check_inbox(mail_token)
    if link:
        driver.get(link)
        time.sleep(5)

    driver.quit()

    return f"Email: {email}\nUsername: {username}\nPassword: {password}\nToken: {local_token}"

@bot.command()
async def caccnt(ctx, num: int):
    await ctx.reply(f"Creating {num} accounts. Please wait...")

    tokens = []
    for _ in range(num):
        try:
            acc = await create_account()
            if acc:
                tokens.append(acc)
            else:
                tokens.append("Account creation failed.")
        except Exception as e:
            tokens.append(f"Error: {str(e)}")

    for t in tokens:
        await ctx.author.send(t)

bot.run(TOKEN)
