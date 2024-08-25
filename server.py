import os
import shutil

from dotenv import load_dotenv
from flask import Flask, request
from git import Repo
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.config['KAARAH_FOLDER'] = 'repo/divrei_torah/kaarah'
app.config['MAAMAREI_MORDECHAI_FOLDER'] = 'repo/divrei_torah/maamarei_mordechai'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

username = os.getenv('GITHUB_USERNAME')
password = os.getenv('GITHUB_TOKEN')
repository = os.getenv('GITHUB_REPO')
remote = f"https://{username}:{password}@github.com/{username}/{repository}.git"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def update_html_file(uploaded_files, titles):
    shutil.rmtree('repo', ignore_errors=True)
    with Repo.clone_from(remote, "repo") as repo:
        changed_files = []
        kaarah_titles = []
        maamarei_titles = []

        for file, title in zip(uploaded_files, titles):
            file = str(file)
            if file.lower().startswith('kaarah'):
                directory = app.config['KAARAH_FOLDER']
                kaarah_titles.append(title)
            else:
                directory = app.config['MAAMAREI_MORDECHAI_FOLDER']
                maamarei_titles.append(title)

            destination = str(os.path.join(directory, os.path.basename(file)))
            shutil.move(file, destination)

            changed_files.append((directory.removeprefix('repo') + "/" + file.replace('\\', '/')).removeprefix('/'))

        repo.git.add(changed_files)
        message = f"Added {', '.join(maamarei_titles)}{' and ' if maamarei_titles and kaarah_titles else ''}{', '.join(kaarah_titles)}"
        repo.index.commit(message)
        origin = repo.remote(name="origin")
        origin.push()


@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = []
    titles = []
    file_entries = request.files.getlist('file')

    for idx, file_entry in enumerate(file_entries):
        if file_entry and allowed_file(file_entry.filename):
            title_key = f'title_{idx + 1}'
            title = request.form.get(title_key)
            titles.append(title)

            filename = file_entry.filename.replace(' ', '_')
            file_entry.save(filename)
            uploaded_files.append(filename)

    update_html_file(uploaded_files, titles)

    return f"Files uploaded: {uploaded_files}\nTitles: {titles}\n\nSuccess"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
