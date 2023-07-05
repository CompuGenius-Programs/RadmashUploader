import os
import shutil

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, request
from git import Repo, rmtree
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
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# def update_html_file(uploaded_files, titles):
#     for file, title in zip(uploaded_files, titles):
#         if title.startswith('Kaarah'):
#             filename = 'kaarah.html'
#         else:
#             filename = "maamarei_mordechai.html"
#
#         with open(filename, 'r+', encoding="utf-8") as f:
#             soup = BeautifulSoup(f, 'html.parser')
#             target_ul = soup.find('ul', {'id': 'file-list'})
#             li_tag = soup.new_tag('li')
#             fname = "/%s" % file.replace('\\', '/')
#             a_tag = soup.new_tag('a', href=fname, target='blank')
#             a_tag.string = title
#             li_tag.append(a_tag)
#             target_ul.append(li_tag)
#
#             f.seek(0)
#             f.write(str(soup.prettify()))
#             f.truncate()


def update_html_file(uploaded_files, titles):
    with Repo.clone_from(remote, "repo") as repo:
        changed_files = []

        for file, title in zip(uploaded_files, titles):
            if title.startswith('Kaarah'):
                fname = 'kaarah.html'
                directory = app.config['KAARAH_FOLDER']
            else:
                fname = 'maamarei_mordechai.html'
                directory = app.config['MAAMAREI_MORDECHAI_FOLDER']

            if fname not in changed_files:
                changed_files.append(fname)
            filename = "repo/" + fname
            shutil.move(file, os.path.join(directory, os.path.basename(file)))

            with open(filename, 'r+', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                target_ul = soup.find('ul', {'id': 'file-list'})
                li_tag = soup.new_tag('li')
                fname = "%s/%s" % (directory.removeprefix('repo'), file.replace('\\', '/'))
                a_tag = soup.new_tag('a', href=fname, target='blank')
                a_tag.string = title
                li_tag.append(a_tag)
                target_ul.append(li_tag)

                f.seek(0)
                f.write(str(soup.prettify()))
                f.truncate()

            changed_files.append(fname.removeprefix('/'))

        kaarah_titles = [title for title in titles if title.startswith('Kaarah')]
        maamarei_titles = [title for title in titles if not title.startswith('Kaarah')]

        repo.git.add(changed_files)
        repo.index.commit("%s and %s" % (", ".join(maamarei_titles), ", ".join(kaarah_titles)))
        origin = repo.remote(name="origin")
        origin.push()

    rmtree("repo")


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

            filename = secure_filename(file_entry.filename)

            file_entry.save(filename)
            uploaded_files.append(filename)

    update_html_file(uploaded_files, titles)

    return f"Files uploaded: {uploaded_files}\nTitles: {titles}\n\nSuccess"


if __name__ == '__main__':
    app.run(host='localhost', port=8080)
