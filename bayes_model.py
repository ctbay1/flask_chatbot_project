import pandas as pd
from user_defined import preprocess_text_v4
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

df = pd.read_csv('intent_data.csv')

df['utterance'] = df['utterance'].apply(preprocess_text_v4)

X = df['utterance']
y = df['intent']

vectorizer = CountVectorizer(ngram_range=(1,3))
X = vectorizer.fit_transform(X)

classifier = MultinomialNB()
classifier.fit(X, y)

probability_threshold = 0.2