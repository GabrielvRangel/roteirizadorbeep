import model
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import datetime

ALLOWED_EXTENSIONS = set(['csv'])

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
upload_folder = os.path.join(os.getcwd(), 'upload')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/roteirizar",methods=["GET","POST"])
def roteirizar():
    data = request.args.get('data')
    hub = request.args.get('hub')
    produto = request.args.get('produto')
    tempo = request.args.get('tempo')   
    Sessão = model.Roteirização(data, hub, produto, tempo)
    if not data or not hub or not produto or not tempo:
        mensagem = 'Favor preencher todos os campos corretamente!'
        return render_template("index.html", error=mensagem)
    else: 
        Sessão.Roteirizar()
        return render_template("mapa.html"), download()

def download():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        new_filename = f'{filename.split(".")[0]}_{str(datetime.now())}.csv'
        save_location = os.path.join('input', new_filename)
        file.save(save_location)
        output_file = model.file_name(save_location)
        return send_from_directory('output', output_file)


if __name__ == "__main__":
    app.run()