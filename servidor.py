import model
import os
from flask import Flask, render_template
from flask import request
from werkzeug.utils import secure_filename

app = Flask(__name__)
upload_folder = os.path.join(os.getcwd(), 'dados')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods="POST")
def upload():
    file = request.files['planilha']
    savePath = os.path.join(upload_folder, secure_filename(file.filename))
    file.save(savePath)
    return 'feito com sucesso'

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
        return render_template("mapa.html")

if __name__ == "__main__":
    app.run()