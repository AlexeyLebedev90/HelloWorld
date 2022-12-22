
import re
import sqlite3
import pandas as pd
import pymorphy2
from nltk.corpus import stopwords


DB_NAME = "descriptions2.db"
IN_TABLE = 'hh_descriptions'
OUT_TABLE = 'hh_tokens'


def tokenize(s):
    morph = pymorphy2.MorphAnalyzer()
    tokens = re.findall("[\/\-а-яёa-z]+", s.lower())
    filtered = [morph.parse(i)[0].normal_form for i in tokens if i not in stopwords.words("russian")]  # нормализация - лемматизация
    return filtered


def preprocess_data(con, in_table_name, out_table_name):
    print('Start tokenizing')

    cur = con.cursor()
    try:
        cur.execute(f"DROP TABLE {out_table_name}")
    except Exception as e:
        print(e)
    cur.execute(f"CREATE TABLE {out_table_name}(hhid, title, tokens, skills, url)")
    con.commit()
        
    df = pd.read_sql_query(f"SELECT * FROM {in_table_name}", con)
    print(df.shape)
    df_tokens = df.copy()
    df_tokens['tokens'] = df_tokens.apply(lambda row: ' '.join(tokenize(row['description'])), axis=1)   # 9мин 15сек
    print(df_tokens.shape)
    df_tokens.to_sql(out_table_name, con, if_exists='replace')


if __name__ == '__main__':
    try:
        con = sqlite3.connect(DB_NAME)
        preprocess_data(con, IN_TABLE, OUT_TABLE)
    except Exception as e:
        print(e)
    finally:
        con.close()

