import re
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from collections import Counter
import pandas as pd

# variables for app.py
  #inventory
products = pd.read_csv('inventory.csv')
products = products.to_dict('records')

stop_words = set(stopwords.words('english'))
normalizer = WordNetLemmatizer()

sizes = {
    'xs': 'extra small',
    's': 'small',
    'm': 'medium',
    'l': 'large',
    'xl': 'extra large',
    'xxl': 'double extra large',
    # Add more size abbreviations and their corresponding sizes as needed
}

colors_list = []
with open('wikipedia-list-of-colors.txt') as colors_txt:
    for color in colors_txt.readlines():
        colors_list.append(color.lower().strip('\n'))

# functions
def preprocess(input_sentence):
    input_sentence = input_sentence.lower() #convert to lower case
    input_sentence = re.sub(r'[^\w\s]', '', input_sentence) #remove punctuation marks, non-alphanumeric characters
    tokens         = word_tokenize(input_sentence)
    input_sentence = [token for token in tokens if not token in stop_words] #remove stop words: a, an, the, etc.
    return input_sentence

def compare_overlap(user_message, possible_response):
    similar_words = 0
    for token in user_message:
        if token in possible_response:
              similar_words += 1
    return similar_words

def extract_nouns(tagged_message):
     message_nouns = [token[0] for token in tagged_message if token[1].startswith('N')]
     return message_nouns

def compute_similarity(tokens, categories):
     output_list = [[token.text, category.text, token.similarity(category)] for token in tokens for category in categories]
     return output_list

def get_part_of_speech(word):
  probable_part_of_speech = wordnet.synsets(word)
  pos_counts = Counter()
  pos_counts["n"] = len(  [ item for item in probable_part_of_speech if item.pos()=="n"]  )
  pos_counts["v"] = len(  [ item for item in probable_part_of_speech if item.pos()=="v"]  )
  pos_counts["a"] = len(  [ item for item in probable_part_of_speech if item.pos()=="a"]  )
  pos_counts["r"] = len(  [ item for item in probable_part_of_speech if item.pos()=="r"]  )
  most_likely_part_of_speech = pos_counts.most_common(1)[0][0]
  return most_likely_part_of_speech

def preprocess_text(text):
  cleaned = re.sub(r'\W+', ' ', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized])
  return normalized
  
def preprocess_text_v2(text):
  cleaned = re.sub(r'\W+', ' ', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized if not token in stop_words])
  return normalized

def preprocess_text_v3(text):
  cleaned = re.sub(r'[^\w\s]', '', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized])
  return normalized

def preprocess_text_v3_2(text):
  cleaned = re.sub(r'[^\w\s -]', '', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized])
  return normalized

def preprocess_text_v4(text):
  cleaned = re.sub(r'[^\w\s -]', '', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized if not token in stop_words])
  return normalized

def preprocess_text_v4_2(text):
  cleaned = re.sub(r'[^\w\s -]', '', text).lower()
  tokenized = word_tokenize(cleaned)
  normalized = " ".join([normalizer.lemmatize(token, get_part_of_speech(token)) for token in tokenized if not token in stop_words])
  return normalized

def compute_similarity_v2(token, categories, lst):
     for category in categories:
          lst.append([token.text, category.text, token.similarity(category)])

def preprocess_v2(input_sentence):
    input_sentence = input_sentence.lower() #convert to lower case
    input_sentence = re.sub(r'[^\w\s]', '', input_sentence) #remove punctuation marks, non-alphanumeric characters
    tokens         = word_tokenize(input_sentence)
    return tokens

def preprocess_v3(input_sentence):
    input_sentence = input_sentence.lower() #convert to lower case
    input_sentence = re.sub(r'[^\w\s]', '', input_sentence) #remove punctuation marks, non-alphanumeric characters
    return input_sentence

def get_part_of_the_day(current_time_obj):
    time_hour     = current_time_obj.hour
    greeting_text = ''
    if time_hour < 12:
        greeting_text = "Good Morning!"
    elif time_hour < 18:
        greeting_text = "Good Afternoon!"
    else:
        greeting_text = "Good Evening!"
    return greeting_text

placeholder_messages_list = [
  "How can I reset my password?",
  "I forgot my password. Can you help me?",
  "Do you sell hats?",
  "Do you have any medium-sized red t-shirts in stock?",   
  "What is my order status?",
  "What is the latest update on my recent purchase?",
  "Do you offer free shipping?",
  "Where can I see my order history?",
  "Can you add small denim shorts to my cart?",
  "Could you put that white xl t-shirt to my shopping cart?"
]