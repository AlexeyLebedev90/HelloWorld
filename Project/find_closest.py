import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import gensim
import sqlite3
import numpy as np
import json
import traceback


from preprocess import tokenize


class TFIDFVac:
    def __init__(self, con, n_top=10):
        self.con = con
        self.tokens_df = pd.read_sql_query("SELECT * FROM hh_tokens", self.con)
        self.model = None
        self.tfidf_wm = None
        self.tfidf_tokens = None
        self.df_tfidfvect = None
        self.n_top = n_top

    def fit(self):
        self.model = TfidfVectorizer(analyzer='word', stop_words='english')
        self.tfidf_wm = self.model.fit_transform(self.tokens_df.tokens)
        self.tfidf_tokens = self.model.get_feature_names_out()
        self.df_tfidfvect = pd.DataFrame(data=self.tfidf_wm.toarray(), columns=self.tfidf_tokens)

    def _find_top_closest_ids(self, resume_text, ntop):
        resume_df = pd.DataFrame(self.model.transform([' '.join(tokenize(resume_text))]).toarray(), columns=self.tfidf_tokens)
        df2 = pd.DataFrame(cosine_similarity(self.tfidf_wm, resume_df, dense_output=True), columns=['score'])
        closest_ids = df2.sort_values('score', ascending=False).iloc[:ntop]
        return closest_ids

    def _get_vacs_from_ids(self, ids):
        return ids.join(self.tokens_df, how='inner')[["title", "description", "url", "score"]]\
            .to_json(orient="records", force_ascii=False)
    
    def get_matching_vacancies(self, resume_text):
        ids = self._find_top_closest_ids(resume_text, self.n_top)
        res = self._get_vacs_from_ids(ids)
        return res


class Word2VecVac(TFIDFVac):
    def __init__(self, con, n_top=10):
        self.con = con
        self.tokens_df = pd.read_sql_query("SELECT * FROM hh_tokens", self.con)
        self.tokens = None
        self.model = None
        self.mean_embedding_vectorizer = None
        self.vac_mean_embedded = None
        self.n_top = n_top

    def fit(self):
        self.tokens = self.tokens_df['tokens'].apply(lambda x: x.split(' '))
        self.model = gensim.models.Word2Vec(self.tokens, vector_size=100, window=5, min_count=1, workers=4)
        self.mean_embedding_vectorizer = self.MeanEmbeddingVectorizer(self.model)
        self.vac_mean_embedded = self.mean_embedding_vectorizer.transform(self.tokens, to_tokenize=False)

    def _find_top_closest_ids(self, resume_text, ntop):
        resume_embedded = self.mean_embedding_vectorizer.transform([resume_text])
        similarity_df = pd.DataFrame(data=cosine_similarity(resume_embedded, self.vac_mean_embedded)[0], columns=['score'])
        top_scores = similarity_df.sort_values('score', ascending=False).iloc[:ntop]
        return top_scores

    class MeanEmbeddingVectorizer(object):
        def __init__(self, word2vec):
            self.word2vec = word2vec
            # если текст пуст, мы должны вернуть нулевой вектор
            # с той же размерностью, что и все остальные векторы
            self.dim = self.word2vec.wv.vector_size

        def fit(self, X, y=None):
            return self

        def transform(self, X, to_tokenize=True):
            if to_tokenize:
                X = [tokenize(i) for i in X]

            return np.array([
                np.mean([self.word2vec.wv[w] for w in words if w in self.word2vec.wv]
                        or [np.zeros(self.dim)], axis=0)
                for words in X
            ])
        
        def fit_transform(self, X, y=None):
            return self.transform(X)



if __name__ == '__main__':
    resume_text = 'Data Scientist с опытом работы в проектах по продвинутой аналитике и исследованиях. Успешно реализовал проекты включая промышленные решения \
        для клиентов из различных областей: потребительские товары, ритейл, медицинские приборы и другие. Имеет страсть к автоматизации \
        на основе данных. Европейское гражданство. Разработка, алгоритмы, машинное обучение, проведение интервью\
        Data Science, Leadership, R&D, Machine Learning, Software Developement, Algorithms, Agile, Interviewing \
        Python (numpy, pandas, scipy, sklearn, matplotlib, seaborn, requests), DevOps (Linux, Git, Docker), Cloud (MS Azure, AWS),\
        WEB (Flask, Figma, HTML, CSS), Business Intelligence (Power BI), SQL'
    
    try:
        DB_NAME = "descriptions2.db"
        con = sqlite3.connect(DB_NAME)

        vac_model = TFIDFVac(con)
        vac_model.fit()
        print(vac_model.get_matching_vacancies(resume_text))
        print()
        w2v_model = Word2VecVac(con)
        w2v_model.fit()
        print(w2v_model.get_matching_vacancies(resume_text))
    except Exception as e:
        print(traceback.format_exc())
    finally:
        con.close()


