import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    current_user, login_required
)

# -------------------- APP --------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = '144313526'

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# -------------------- DATABASE --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sqlite.db")

connection = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = connection.cursor()

# -------------------- USER MODEL --------------------
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    row = cursor.execute(
        'SELECT id, username, password_hash FROM user WHERE id = ?',
        (user_id,)
    ).fetchone()
    if row:
        return User(row[0], row[1], row[2])
    return None

# -------------------- ROUTES --------------------
@app.route('/')
def index():
    cursor.execute('''
        SELECT post.id, post.title, post.content, post.author_id,
               user.username,
               COUNT(like.id) AS likes,
               COALESCE(post.edited, 0)
        FROM post
        JOIN user ON post.author_id = user.id
        LEFT JOIN like ON post.id = like.post_id
        GROUP BY post.id
    ''')

    rows = cursor.fetchall()
    posts = []

    for row in reversed(rows):
        posts.append({
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'author_id': row[3],
            'username': row[4],
            'likes': row[5],
            'edited': bool(row[6]),
            'is_liked': False
        })

    if current_user.is_authenticated:
        liked_rows = cursor.execute(
            'SELECT post_id FROM like WHERE user_id = ?',
            (current_user.id,)
        ).fetchall()

        liked_ids = {r[0] for r in liked_rows}

        for post in posts:
            post['is_liked'] = post['id'] in liked_ids

    return render_template('blog.html', posts=posts)


@app.route('/add/', methods=['GET', 'POST'])
@login_required
def add_post():
    message = ''

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            message = 'Type something!'
            return render_template('add_post.html', message=message)

        cursor.execute(
            'INSERT INTO post (title, content, author_id) VALUES (?, ?, ?)',
            (title, content, current_user.id)
        )
        connection.commit()
        return redirect(url_for('index'))

    return render_template('add_post.html', message=message)


@app.route('/post/<int:post_id>')
def post(post_id):
    row = cursor.execute('''
        SELECT post.id, post.title, post.content,
               post.author_id, user.username,
               COALESCE(post.edited, 0)
        FROM post
        JOIN user ON post.author_id = user.id
        WHERE post.id = ?
    ''', (post_id,)).fetchone()

    if not row:
        return 'Post not found', 404

    likes = cursor.execute(
        'SELECT COUNT(*) FROM like WHERE post_id = ?',
        (post_id,)
    ).fetchone()[0]

    is_liked = False
    if current_user.is_authenticated:
        is_liked = cursor.execute(
            'SELECT 1 FROM like WHERE user_id = ? AND post_id = ?',
            (current_user.id, post_id)
        ).fetchone() is not None

    post_data = {
        'id': row[0],
        'title': row[1],
        'content': row[2],
        'author_id': row[3],
        'username': row[4],
        'likes': likes,
        'is_liked': is_liked,
        'edited': bool(row[5])
    }

    return render_template('post.html', post=post_data)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    message = ''

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            message = 'Enter username and password'
            return render_template('register.html', message=message)

        try:
            cursor.execute(
                'INSERT INTO user (username, password_hash) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            connection.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            message = 'This user already exists'

    return render_template('register.html', message=message)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    message = ''

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        row = cursor.execute(
            'SELECT id, username, password_hash FROM user WHERE username = ?',
            (username,)
        ).fetchone()

        if row and check_password_hash(row[2], password):
            login_user(User(row[0], row[1], row[2]))
            return redirect(url_for('index'))

        message = 'Wrong username or password, try again'

    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    cursor.execute(
        'DELETE FROM post WHERE id = ? AND author_id = ?',
        (post_id, current_user.id)
    )
    connection.commit()
    return redirect(url_for('index'))


@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    liked = cursor.execute(
        'SELECT 1 FROM like WHERE user_id = ? AND post_id = ?',
        (current_user.id, post_id)
    ).fetchone()

    if liked:
        cursor.execute(
            'DELETE FROM like WHERE user_id = ? AND post_id = ?',
            (current_user.id, post_id)
        )
    else:
        cursor.execute(
            'INSERT INTO like (user_id, post_id) VALUES (?, ?)',
            (current_user.id, post_id)
        )

    connection.commit()
    return redirect(url_for('index'))


# -------------------- EDIT POST --------------------
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    row = cursor.execute(
        'SELECT id, title, content, author_id FROM post WHERE id = ?',
        (post_id,)
    ).fetchone()

    if not row:
        return 'Post not found', 404

    if int(row[3]) != int(current_user.id):
        return 'No no no mr fish...', 403

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not title or not content:
            post = {'id': row[0], 'title': title, 'content': content}
            return render_template('edit_post.html', post=post, message='Заполните все поля')

        cols = [c[1] for c in cursor.execute("PRAGMA table_info(post)").fetchall()]
        if "edited" not in cols:
            cursor.execute("ALTER TABLE post ADD COLUMN edited INTEGER DEFAULT 0")

        cursor.execute(
            'UPDATE post SET title = ?, content = ?, edited = 1 WHERE id = ?',
            (title, content, post_id)
        )
        connection.commit()
        return redirect(url_for('post', post_id=post_id))

    post = {'id': row[0], 'title': row[1], 'content': row[2]}
    return render_template('edit_post.html', post=post, message='')


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True)
