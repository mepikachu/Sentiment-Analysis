import sqlite3
import joblib
from tensorflow.keras.models import load_model
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
import pandas as pd
import reddit

def load_model(model_name:str):
    # load the model to make the predictions
    #model = joblib.load(model_name)
    model = load_model(model_name)
    return model

def load_database():
    # load and returns the connection to the database
    conn = sqlite3.connect("data/main.db")
    cursor = conn.cursor()
    cursor.execute( """
                    CREATE TABLE IF NOT EXISTS classifications(
                        postid INTEGER PRIMARY KEY AUTOINCREMENT,
                        total_comments INT DEFAULT 0,
                        toxic INT DEFAULT 0,
                        severe_toxic INT DEFAULT 0,
                        obscene INT DEFAULT 0,
                        threat INT DEFAULT 0,
                        insult INT DEFAULT 0,
                        identity_hate INT DEFAULT 0
                    );  
                    """)
    
    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS post_text(
                        postid INTEGER PRIMARY KEY,
                        full_text TEXT,
                        FOREIGN KEY (postid) REFERENCES classifications(postid) ON UPDATE CASCADE ON DELETE CASCADE
                    );
                   """)

    conn.commit()

    return conn, cursor

def insertEntry(conn, cursor, post_text:str, postid:int=-1):
    # insert a new empty record into the table and returns it's postid
    if (postid == -1):
        cursor.execute(f"""
                        INSERT INTO classifications(total_comments) VALUES(0);
                    """)
        postid = cursor.lastrowid
        cursor.execute(f"""
                        INSERT INTO post_text(postid, full_text) VALUES(?, ?);
                    """, (postid, post_text))
    
    else:
        cursor.execute(f"""
                        INSERT INTO classifications(postid) VALUES(?);
                    """, (postid))
        cursor.execute(f"""
                        INSERT INTO post_text(postid, full_text) VALUES(?, ?);
                    """, (postid, post_text))

    conn.commit()
    return postid

def predictUpdate(conn, cursor, model, vectorizer, postid:int, comment_text:str):
    # predict the labels and update in the database
    #comment_vector = vectorizer.transform([comment_text])
    #prediction = model.predict(comment_vector)[0]
    comment_seq = tokenizer.texts_to_sequences([comment_test])
    comment_pad = pad_sequences(comment_seq, maxlen=max_len)
    prediction = ((model.predict(comment_pad) > 0.5).astype(int))[0]
    cursor.execute(f"""
                   UPDATE classifications SET total_comments = total_comments + 1,
                                             toxic = toxic + {prediction[0]}, 
                                             severe_toxic = severe_toxic + {prediction[1]},
                                             obscene = obscene + {prediction[2]},
                                             threat = threat + {prediction[3]},
                                             insult = insult + {prediction[4]},
                                             identity_hate = identity_hate + {prediction[5]}
                    WHERE postid = {postid};                   
                   """)
    conn.commit()

    for pred in prediction:
        if (pred == 1):
            return 1
    return 0

def generate_charts(conn, cursor, postid: int):
    # Fetch the classification data for the postid
    cursor.execute(f"SELECT * FROM classifications WHERE postid = {postid};")
    result = cursor.fetchone()
    
    if result is None:
        print(f"No record found for postid: {postid}")
        return
    
    print(result)
    
    labels = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
    total_comments = result[1]  # Get the total_comment count
    counts = result[2:]  # Exclude postid and total_comments
    
    if total_comments == 0:
        print(f"No comments to calculate percentages for postid: {postid}")
        return
    
    # Calculate percentages
    percentages = [(count / total_comments) * 100 for count in counts]
    
    # Create bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(labels, percentages, color='skyblue')
    plt.xlabel('Categories')
    plt.ylabel('Percentage')
    plt.title(f'Comment Classification Percentages for Post ID: {postid}')
    plt.ylim(0, 100)  # Set y-axis limits from 0 to 100
    plt.savefig(f'results/postid_{postid}')

# Load training data
tokenizer = joblib.load("models/tokenizer.pkl")
model = load_model('models/toxic_rnn_classifier.h5')
conn, cursor = load_database()

# fetch posts from a subreddit
negative_comments = {}
posts = reddit.getData(SUBREDDITS = ['insanepeoplefacebook'])
for post in posts:
    id = insertEntry(conn, cursor, post['title'])
    negative_comments[id] = {}
    for comment in post['comments']:
        pred = predictUpdate(conn, cursor, model, tokenizer, id, comment)
        if (pred == 1):
            (negative_comments[id]).append(comment)

for i in range(1, len(posts)+1):
    generate_charts(conn, cursor, postid=i)