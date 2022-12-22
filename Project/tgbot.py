import os
from dotenv import load_dotenv
import telebot
import sqlite3
import json

from find_closest import TFIDFVac, Word2VecVac

load_dotenv()

# https://t.me/setkjaglskhg_bok_bot

#MODEL_TYPE = 'tfidf'
MODEL_TYPE = 'word2vec'

bot = telebot.TeleBot(os.getenv("TOKEN"))

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, text=MODEL_TYPE)
    for i in json.loads(model.get_matching_vacancies(message.text)):
        reply = '\n'.join(str(i) for i in i.values())
        if len(reply) > 4095:
            for x in range(0, len(reply), 4095):
                bot.reply_to(message, text=reply[x:x+4095])
        else:
            bot.reply_to(message, text=reply)


if __name__ == '__main__':
    try:
        con = sqlite3.connect(os.getenv("DB_NAME"))

        if MODEL_TYPE == 'tfidf':
            model = TFIDFVac(con, n_top=10)
        elif MODEL_TYPE == 'word2vec':
            model = Word2VecVac(con, n_top=10)
        model.fit()

        bot.infinity_polling()
    except Exception as e:
        print(e)
    finally:
        con.close()
