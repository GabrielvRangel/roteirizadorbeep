import model
import os
from flask import Flask, render_template
from flask import request

app = Flask(__name__)

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
        return render_template("mapa.html")

if __name__ == "__main__":
    app.run(debug=True)