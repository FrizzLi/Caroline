##########################################
#
# A script to auto generate vocabulary
#   from the given input Korean text
#
##########################################

# print debug info
print('Loading...')
    
# packages
from konlpy.tag import Okt
import requests
from bs4 import BeautifulSoup
import json
import csv

# vocabulary
vocabulary = []

# print debug info
print('Creating tokenizer instance...')

# create OKT instance
okt = Okt();

korean_text = ''

# open input file
with open('korean.txt') as f:
    # init input text
    korean_text = f.read()
    
    # print debug info
    print('Tokenizing Korean text...', end='')

    # tokenize text
    tokenized_text = okt.pos(korean_text, norm=True, stem=True)
    
    # print debug info
    print('Done')

# append full sentence to the list of tokens
tokenized_text.append((korean_text, 'Full sentence'))

# word count
count = 0

# loop over tokens
for token in tokenized_text:
    try:
        # translate.com POST request data payload
        payload = {
            'text_to_translate': token[0],
            'source_lang': 'ko',
            'translated_lang': 'en',
            'use_cache_only': 'false'
        }

        # make HTTP POST request to translate.com
        response = requests.post(
            'https://www.translate.com/translator/ajax_translate',
            headers={'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'}, # change to any if daily dose of requests is exhausted
            data=payload
        )

        # parse the response
        translated_text = json.loads(response.text)['translated_text']
        
        # print debug info
        count += 1
        print('Translating...', token[0] + ': ',
               translated_text, ', Type:',
               token[1], ', word',
               count,
               'out of', len(tokenized_text),
               ' words')
        
        # init details
        congation_details = []
        
        # optionally request conjugation details
        if (token[1] in ['Verb', 'Adverb', 'Adjective']):
            # get conjugation details
            response = requests.get('https://koreanverb.app/?search=' + token[0])

            # parse the content
            content = BeautifulSoup(response.text, 'lxml')

            # extract HTML table
            table = content.find('table')

            # extract table data
            conjugation_details = list(filter(None, [
                ': '.join([col.text.replace('declarative ', '').replace(' informal high', '') for col in row.find_all('td')])
                for row in
                table.find_all('tr')
                if 'declarative present informal high' in row.text or
                   'declarative past informal high' in row.text or
                   'declarative future informal high' in row.text
            ]))
            
            # print debug info
            print('Conjugating...', token[0] + ': ', conjugation_details)
        
        # skip punctuation, foreign words and duplicates
        try:
            if (token[1] == 'Punctuation' or token[1] == 'Foreign'):
                # print debug info
                print('Skipping garbage...')
                continue
        except Exception as e:
            print('Error skipping token:', e)

        # append token to vocabulary
        vocabulary.append({
            'Word': token[0],
            'Type': token[1],
            'Translation': translated_text,
            'Present tense': '',
            'Past tense': '',
            'Future tense': ''
        })
        
        try:
            if (token[1] in ['Verb', 'Adverb', 'Adjective']):
                vocabulary[-1]['Present tense'] = conjugation_details[0].split(': ')[-1]
                vocabulary[-1]['Past tense'] = conjugation_details[1].split(': ')[-1]
                vocabulary[-1]['Future tense'] = conjugation_details[2].split(': ')[-1]
        
        except:
            pass

    except:
        print('Failed to translate: ', token)

# vocabulary
# korean_text   # korean_text.replace('\n', '<br>'),

# write HTML file
with open('./html/vocabulary.html', 'w') as f:
    f.write(html_output)





















