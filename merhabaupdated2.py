import time
import irc.bot
import threading
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup

server = "irc.libera.chat"
channel = "#rebel"
nickname = "timerirq"
previous_messages = []
last_sent_outputs = ["", "", "", "", ""]  # List to store the last 5 messages sent to the channel
current_nick = ""  # Variable to store current nick

class RepeatingTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def send_message_in_chunks(connection, channel, message, chunk_size=300):
    lines = message.split("\n")  # Split the message into lines
    for line in lines:
        line = line.replace("\r", "").replace("\n", "")
        line = line.strip()  # Remove leading and trailing whitespace
        if line:  # If the line is not empty, send it
            while len(line) > 0:
                chunk = line[:chunk_size]
                connection.privmsg(channel, f"  {chunk}")  # Add two spaces (tabs) before each line
                line = line[chunk_size:]
                time.sleep(2)  # Wait for 2 seconds after each chunk


class IRCBot(irc.bot.SingleServerIRCBot):
    def __init__(self, driver):
        server_info = irc.bot.ServerSpec(server, 6667, "timer")
        irc.bot.SingleServerIRCBot.__init__(self, [server_info], nickname, nickname)
        self.driver = driver

    def on_welcome(self, connection, event):
        connection.privmsg("NickServ", "IDENTIFY timer password")
        connection.join(channel)
        global last_sent_outputs
        last_sent_outputs[0] = get_all_elements(self.driver)
        send_message_in_chunks(self.connection, channel, last_sent_outputs[0])
        self.repeating_timer = RepeatingTimer(3, self.update_elements)
        self.repeating_timer.start()
        if channel not in self.channels:
           connection.join(channel)

    def on_pubmsg(self, connection, event):
        global current_nick
        nick = event.source.nick
        message = event.arguments[0]

        if nick != current_nick:
            current_nick = nick

        if event.target == channel and nick in ["cloudowind", "fission", "mur", "phadthai", "babyrobbe"]:
            if f"{nickname}:" in message:
                command = message.split(f"{nickname}:")[1].strip()
                input_box = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, 'prompt-textarea')))
                input_box.send_keys(command)
                input_box.send_keys(Keys.RETURN)

        if "http" in message:
            urls = message.split()
            for url in urls:
                if url.startswith("http"):
                    title, description = self.get_url_info(url)
                    info_message = f"Title: {title} | Description: {description}"
                    connection.privmsg(channel, info_message)

    def update_elements(self):
        global last_sent_outputs
        global current_nick

        new_output = get_all_elements(self.driver)
        diff_output = new_output

        for i in range(5):
            diff_output = diff_output.replace(last_sent_outputs[i], "")

        if diff_output:
            if current_nick:
                diff_output = f"{current_nick}: {diff_output}"
                current_nick = ""

        last_sent_outputs.pop(0)
        last_sent_outputs.append(new_output)

        remaining_output = get_all_elements(self.driver)
        remaining_output = remaining_output.replace(diff_output, "")
        diff_output += remaining_output

        send_message_in_chunks(self.connection, channel, diff_output)
        time.sleep(3)
    def get_url_info(self, url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No title found"
            description = soup.find('meta', attrs={'name': 'description'})
            description = description['content'].strip() if description else "No description found"
            return title, description
        except Exception as e:
            print("Error fetching URL info:", e)
            return "Error", "Error fetching URL info"

def get_all_elements(driver):
    WebDriverWait(driver, 120).until(EC.invisibility_of_element_located((By.XPATH, "//button[@aria-label='Stop generating']")))
    elements = driver.find_elements(By.XPATH, "//p | //code[@class] | //li")  # Include <li> elements in the XPath query
    output = ""
    for element in elements:
        if element.tag_name in ["p", "code", "li"]:  # Check for <code class> and <li> elements as well
            message = element.text.strip()  # Remove leading and trailing whitespace from the message
            if message and message not in previous_messages:  # If the message is not empty and has not been added previously
                output += message + "\n"  # Add a newline after each message
                previous_messages.append(message)  # Only add the message content to the list
    return output.strip()

if __name__ == "__main__":
    driver = webdriver.Firefox()
    driver.get('https://chat.openai.com/')
    bot = IRCBot(driver)
    bot.start()
