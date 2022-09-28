import model
import os
from flask import Flask, render_template, request, send_file

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

if __name__ == "__main__":
    app.run()

class Mapa:
    def Baixar():
        #Enviando para o mapa
        render_template("mapa.html")
        #Enviando o arquivo roteirizado para download
        send_file("Road.xlsx", as_attachment=True)