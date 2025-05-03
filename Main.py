
import discord
import time, random, string, json, requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

TOKEN = "MTM2MzQ0MzE1OTAwNjMxNDY2OA.GvCZMH.u0VnJEI-NPDlwvF7c4NFlCLnoix96vrZdpSzHg"
CAPMONSTER_KEY = "3fdf7e4881366ecd820f6f48686f4bc8"

intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)

def get_temp_email():
    domain = requests.get("https://api.mail.tm/domains").json()["hydra:member"][0]["domain"]
    local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{local}@{domain}"
    password = "TempPass123"
    
    requests.post("https://api.mail.tm/accounts", json={"address": email, "password": password})
    token = requests.post("https://api.mail.tm/token", json={"address": email, "password": password}).json()["token"]
    return email, password, token

def wait_for_email_verify(token):
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(60):
        msgs = requests.get("https://api.mail.tm/messages", headers=headers).json()["hydra:member"]
        for msg in msgs:
            if "Verify Email Address" in msg["subject"]:
                full = requests.get(f"https://api.mail.tm/messages/{msg['id']}", headers=headers).json()
                return "https://" + full["text"].split("https://")[1].split("\n")[0]
        time.sleep(2)
    return None

def solve_captcha(site_key, url):
    task = {
        "clientKey": CAPMONSTER_KEY,
        "task": {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": url,
            "websiteKey": site_key
        }
    }
    task_id = requests.post("https://api.capmonster.cloud/createTask", json=task).json()["taskId"]
    while True:
        res = requests.post("https://api.capmonster.cloud/getTaskResult", json={
            "clientKey": CAPMONSTER_KEY,
            "taskId": task_id
        }).json()
        if res["status"] == "ready":
            return res["solution"]["gRecaptchaResponse"]
        time.sleep(1)

def create_discord_account():
    email, _, mail_token = get_temp_email()
    username = "User" + ''.join(random.choices(string.ascii_letters, k=5))
    password = "Discord123!"

    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    driver = uc.Chrome(options=options)
    driver.get("https://discord.com/register")
    time.sleep(5)

    driver.find_element(By.NAME, "email").send_keys(email)
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password)
    driver.find_element(By.XPATH, '//select[@aria-label="Month"]').send_keys("January")
    driver.find_element(By.XPATH, '//select[@aria-label="Day"]').send_keys("1")
    driver.find_element(By.XPATH, '//select[@aria-label="Year"]').send_keys("2001")

    time.sleep(1)
    sitekey = driver.find_element(By.CLASS_NAME, "h-captcha").get_attribute("data-sitekey")
    captcha = solve_captcha(sitekey, "https://discord.com/register")

    driver.execute_script(f'document.getElementsByName("h-captcha-response")[0].innerHTML="{captcha}";')
    time.sleep(1)
    driver.find_element(By.XPATH, '//button[contains(text(), "Continue")]').click()
    time.sleep(10)

    verify_url = wait_for_email_verify(mail_token)
    if verify_url:
        driver.get(verify_url)
        time.sleep(5)

    # Grab token from local storage
    token = driver.execute_script("return window.localStorage.getItem('token');")
    token = token.strip('"') if token else "TOKEN_NOT_FOUND"
    driver.quit()
    return token

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.content.startswith("$caccnt"):
        try:
            n = int(message.content.split(" ")[1])
            await message.reply(f"Starting creation of {n} account(s). Tokens will be DMed.")
            for i in range(n):
                await message.channel.send(f"Creating account {i+1}...")
                tok = create_discord_account()
                await message.author.send(f"[{i+1}] Token:\n```{tok}```")
            await message.channel.send("All accounts created and sent.")
        except Exception as e:
            await message.reply(f"Error: {e}")

client.run(TOKEN)
  
