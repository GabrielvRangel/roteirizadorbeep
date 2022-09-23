from sqlite3 import Timestamp
from telnetlib import theNULL
#import pandas as pd
import psycopg2 as pg
from sqlalchemy import Time, create_engine
import googlemaps
import json
import datetime
#import folium
from branca.element import Figure
#from folium.plugins import MarkerCluster
#import folium.plugins as plugins
import os

class Roteirização:
    def __init__(self,data, hub, produto, HrFinal):
        self.data = data
        self.hub = hub
        self.produto = produto
        self.HrFinal = HrFinal

    def Roteirizar(self):
         # API para conectar ao Google MAPS e calcular a distancia entre latitude e longitude de um atendimento
        gmaps = googlemaps.Client(key='AIzaSyC8qP_rQDA-yo7TgbW5_ZbWfwxgu8yZ1JE')
        # -------------------------- AJUSTES PARA ROTEIRIZAR -------------------------- #
        bloqueio = 2 #Número necessário para bloquear ( mémoria de calculo já na consulta realizada pelo time de bi )
        BlockHrInicial = datetime.timedelta(minutes=1) #Escolha qual horário mínimo NÃO pode ter entre um slot e outro
        BlockHrFinal = datetime.timedelta(minutes=int(self.HrFinal)) #Escolha qual horário máximo NÃO pode ter entre um slot e outro

        Iniciop6 = 'Jan 1 0001 06:30AM' #Primeiro slot plantonista 6 - 18
        Fimp6 = 'Jan 1 0001 05:00PM' #Ultimo slot plantonista 6 - 18
        Iniciop7 = 'Jan 1 0001 07:50AM' #Primeiro slot plantonista 7 - 19
        Fimp7 = 'Jan 1 0001 06:20PM' #Ultimo slot plantonista 7 - 19
        Iniciod8 = 'Jan 1 0001 08:30AM' #Primeiro slot diarista 8 - 14
        Fimd8 = 'Jan 1 0001 01:10PM' #Ultimo slot diarista 8 - 14
        Iniciod6 = 'Jan 1 0001 06:30AM' #Primeiro slot diarista 6 - 12
        Fimd6 = 'Jan 1 0001 11:10AM' #Ultimo slot diarista 6 - 12
        Iniciod7 = 'Jan 1 0001 07:50AM' #Primeiro slot diarista 7 - 13
        Fimd7 = 'Jan 1 0001 12:10PM' #Ultimo slot diarista 7 - 13

        # ---------------------------- AJUSTE DA CAPACIDADE -------------------------- #
        # Puxando dados da planilha de capacidade da rota (também vai para o front end)
        Placas = pd.read_excel("dados/Capacidade.xlsx", sheet_name= 'Placas',engine='openpyxl') #Puxa os dados da aba Placas, que contém todas as placas disponíveis
        QuantCapacidade = pd.read_excel("dados/Capacidade.xlsx", sheet_name= 'Quantidade',engine='openpyxl') #Puxa os dados da aba Quantidade, para verificar a quantidade da capacidade por escala

        # Declarando variavel de quantidade
        p6 = QuantCapacidade.iloc[0]['Quantidade'] #Puxando a quantidade de técnicas p6 ( plantonista 6 - 18 ) 
        p7 = QuantCapacidade.iloc[1]['Quantidade'] #Puxando a quantidade de técnicas p7 ( plantonista 7 - 19 ) 
        d8 = QuantCapacidade.iloc[2]['Quantidade'] #Puxando a quantidade de técnicas d8 ( diarista 08 - 14 ) 
        d6 = QuantCapacidade.iloc[3]['Quantidade'] #Puxando a quantidade de técnicas d6 ( diarista 6 - 12 )
        d7 = QuantCapacidade.iloc[4]['Quantidade'] #Puxando a quantidade de técnicas d7 ( diarista 7 - 13 )

        usuario = os.environ['usuario']
        senha = os.environ['senha']
        server = os.environ['server']
        banco = os.environ['banco'] 

        # ------------------------ CONECTANDO AO BANCO DE DADOS ---------------------- #
        # Declara a variavel engine conectando ao banco de dados da beep usando servidor, usuario, senha e nome do banco
        engine = create_engine(f"""postgresql://{usuario}:{senha}@{server}/{banco}""")

        #realizando consulta sql ( esse código dentro das """ código """ é uma consulta sql igual fazemos no metabase )
        sql = f"""
        select vouchers as voucher, data_agendamento, hr_agendamento::time, hub, parceiro_nome, tipo_produto as product_type, nome_comprador, tel_comprador, endereco as endereço, latitude, longitude, latitude + longitude as chave, num_slots
        from last_mile.fct_agendamentos_para_roteirizacao_2 
        where data_agendamento = '{self.data}'
        and hub = '{self.hub}' 
        and ( SUBSTRING(parceiro_nome FROM 1 FOR 3) = '{self.produto}' or SUBSTRING(parceiro_nome FROM 10 FOR 3) = '{self.produto}' )
        order by data_agendamento, parceiro_nome, hr_agendamento
        """

        #colocando a consulta sql em uma tabela pandas

        road = pd.read_sql_query(sql, con=engine) #Pegamos a consulta que fizemos e a conexão com servidor e jogamos dentro de uma tabela usando o pandas e chamamos essa tabela de road
        road['voucher'] = road['voucher'].astype(str).str.replace('[','0').str.replace(']','0').str.replace(',','0').str.replace(' ','0') #Substituindo o array de vouchers por número 0 para ficar em formato numerico

        #Colocando os endereços do hub em uma tabela
        HubEndereço = pd.read_excel("dados/Endereço HUB.xlsx", sheet_name= 'Planilha1',engine='openpyxl')
        FiltroHubEndereço = HubEndereço[HubEndereço['HUB'] == self.hub] 
        cores = pd.read_excel("dados/Cores.xlsx", sheet_name= 'Plan1',engine='openpyxl')


        # ------------------------ FUNÇÕES PARA ROTEIRIZAR ---------------------- #
        # função de mover linhas
        def shift_row_to_bottom(df, index_to_shift): #OBS: Toda vez que aparecer essa função, significa que estamos jogando a linha atual para o último local na tabela
            idx = [i for i in df.index if i != index_to_shift] #Verifica a posição da tabela
            return df.loc[idx+[index_to_shift]] #Retorna a tabela com a posição do voucher em ultimo lugar

        #função para converter texto em date hr
        def convert(date_time): #OBS: Toda vez que aparecer essa função, significa que estamos convertendo texto para data hora
            format = '%b %d %Y %I:%M%p' #Diz como deve ficar o formato de data hora
            datetime_str = datetime.datetime.strptime(date_time, format)#Pega o formato atual e transforma em data hora
            return datetime_str #retorna no formato novo

        # ------------------------ COLUNAS PARA ROTEIRIZAR ---------------------- #
        # adicionando colunas novas na tabela atendimentos e agendas
        road['Atendimentos'] = 0 # Coluna atendimentos é a quantidade de atendimentos que tem
        road['Agendas'] = 0 # Coluna agendamentos é a quantidade de agendas que tem
        road['KM'] = '0' # Quantidade de km de um deslocamento para o outro
        road['Tempo'] = '0' # Tempo de atendimento de um local para o outro
        road['Escala'] = '0' # Escala do time
        road['Placa'] = '0' # Placa dos carros

        # ------------------------ VARIÁVEIS PARA ROTEIRIZAR ---------------------- #
        # variaveis para roteirizar
        EixoXRoad = 1 #Essa variavel ajuda a efetuar as movimentações e analises utilizando o eixo X da planilha
        qtdAtendimentos = 2 #Qtd de atendimentos que tem dentro de uma agenda
        qtdAgendas = 1 #Número de cada agenda
        calculoAgenda = 1 #Soma das agendas que estão sendo
        date = datetime.date(1, 1, 1) #Formato de data padrão para ser utilizado na hora das premissas dos horários durante a roteirização
        EscalaReal = 0 #Quantidade de pessoas que precisamos para roteirizar, essa variavel vai subindo com o tempo
        Capacidade  = p6 + p7 + d8 + d6 + d7 #Capacidade de recursos disponíveis para roteirizar
        road.iat[EixoXRoad - 1, 13] = 1 # colocando na primeira linha da coluna atendimentos como 1
        road.iat[calculoAgenda - 1, 14] = 1 # colocando na primeira linha da coluna agenda como 1
        PData = datetime.datetime.combine(date, road.iat[EixoXRoad - 1, 2]) #Primeira data ( data do primeiro atendimento )
        Diarista6h = 'Jan 1 0001 07:50AM' #Data inicio da diarista das 6 horas
        Diarista7h = 'Jan 1 0001 07:00PM' #Data inicio da diarista das 7 horas
        linhas = len(road.index) #Verifica quantas linhas tem dentro de uma tabela
        lat1 = FiltroHubEndereço.iat[0, 3] #Pegando latitude do hub para o atendimento 
        long1 = FiltroHubEndereço.iat[0, 4] #Pegando longitude do hub para o atendimento
        lat2 = road.iat[EixoXRoad -1, 9] #Pegando latitude do voucher do próximo atendimento após o eixo x 
        long2 = road.iat[EixoXRoad -1, 10] #Pegando longitude do próximo atendimento após o eixo x 
        consulta = gmaps.distance_matrix(f'{lat1},{long1}', f'{lat2},{long2}', mode='driving')['rows'][0]['elements'][0] #Colocando distancia do hub ao primeiro atendimento
        road.iat[EixoXRoad -1, 15] = consulta['distance']['text'] #colocando a distancia em uma coluna
        road.iat[EixoXRoad -1, 16] = consulta['duration']['text'] #colocando o tempo de atendimento em outra coluna
        linhasmapa = 1 #quantidade de vezes que o código vai rodar para arrumar o mapa

        # ------------------------ INICIO DA ROTEIRIZAÇÃO ---------------------- #
        # ------------------------ ENCAIXANDO OS PEDIDOS ----------------------- #
        while(linhas > EixoXRoad): #Pede para o código rodar enquanto a variavel linha for maior que a variavel EixoXRoad
            if PData < convert(Diarista6h): #Verifica se a data do primeiro atendimento dentro da tabela é para escala de quem começa as 6h
                FData = convert('Jan 1 0001 05:00PM') # Declara o horário final baseado em que o começo é as 6h
            elif PData < convert(Diarista7h): #Verifica se a data do primeiro atendimento dentro da tabela é para escala de quem começa as 7h
                FData = convert('Jan 1 0001 06:59PM') # Declara o horário final baseado em que o começo é as 7h

            print(road)
            
            #Verifica qual é o tempo entre o próximo atendimento e o atendimento atual
            tempo = datetime.datetime.combine(date, road.iat[EixoXRoad, 2]) - datetime.datetime.combine(date, road.iat[EixoXRoad - 1, 2])

            #Se no atendimento anterior tiver valor maior ou igual ao que time de bi determinou pra bloquear e o atendimento anterior estiver dentro do tempo inicial e final de atendimento
            #Ou se o horário atual do voucher do eixo x atual for maior que o horário final, ele é jogado para o final da lista para ser encaixado em outra agenda
            #Ou se o horário do eixo atual for igual a do eixo anterior e a área atual for igual a área do eixo anterior vai colocar esse pedido para baixo
            if ( road.iat[EixoXRoad - 1, 12] >= bloqueio and tempo > BlockHrInicial and tempo <= BlockHrFinal ) or ( datetime.datetime.combine(date, road.iat[EixoXRoad, 2]) > FData ) or ( road.iat[EixoXRoad, 2] == road.iat[EixoXRoad - 1, 2] and road.iat[EixoXRoad, 4] == road.iat[EixoXRoad - 1, 4] and EixoXRoad != linhas - 1):
                ver = road.index[road['voucher'] == road.iat[EixoXRoad, 0]].astype(str)
                val = ver.str.extract('([0-9]+)').astype(int)
                road = shift_row_to_bottom(road, val.iat[0, 0])

            #Roteirizando caso todas as premissas sejam atendidas
            elif road.iloc[EixoXRoad]['hr_agendamento'] > road.iloc[EixoXRoad - 1]['hr_agendamento'] and road.iloc[EixoXRoad]['parceiro_nome'] == road.iloc[EixoXRoad - 1]['parceiro_nome'] and datetime.datetime.combine(date, road.iat[EixoXRoad, 2]) <= FData:
                lat1 = road.iat[EixoXRoad - 1, 9] #Pegando latitude do voucher do eixo x atual
                long1 = road.iat[EixoXRoad - 1, 10] #Pegando longitude do voucher do eixo x atual
                lat2 = road.iat[EixoXRoad, 9] #Pegando latitude do voucher do próximo atendimento após o eixo x 
                long2 = road.iat[EixoXRoad, 10] #Pegando longitude do próximo atendimento após o eixo x 
                consulta = gmaps.distance_matrix(f'{lat1},{long1}', f'{lat2},{long2}', mode='driving')['rows'][0]['elements'][0] #calculando distancia e tempo de atendimento
                road.iat[EixoXRoad, 15] = consulta['distance']['text'] #colocando a distancia em uma coluna
                road.iat[EixoXRoad, 16] = consulta['duration']['text'] #colocando o tempo de atendimento em outra coluna
                road.iat[EixoXRoad, 13] = qtdAtendimentos # colocando a sequencia de atendimentos
                qtdAtendimentos = qtdAtendimentos + 1 #Deixando a próxima sequencia anotada para a continuação do loop
                EixoXRoad = EixoXRoad + 1 #Deixando o próximo atendimento da sequencia anotada para a continuação do loop

            #Verifica se o atendimento do eixo atual é menor que o do anterior e se ambos estão na mesma sinergia ou se a área atual é diferente da área anterior, para colocar com atendimento 1
            elif ( road.iat[EixoXRoad, 2] <= road.iat[EixoXRoad - 1, 2] and road.iat[EixoXRoad, 4] == road.iat[EixoXRoad - 1, 4] ) or (road.iat[EixoXRoad, 4] != road.iat[EixoXRoad - 1, 4]):
                road.iat[EixoXRoad, 13] = 1 #Colocar como atendimento 1
                lat1 = FiltroHubEndereço.iat[0, 3] #Pegando latitude do hub para o atendimento 
                long1 = FiltroHubEndereço.iat[0, 4] #Pegando longitude do hub para o atendimento
                lat2 = road.iat[EixoXRoad, 9] #Pegando latitude do voucher do próximo atendimento após o eixo x 
                long2 = road.iat[EixoXRoad, 10] #Pegando longitude do próximo atendimento após o eixo x 
                consulta = gmaps.distance_matrix(f'{lat1},{long1}', f'{lat2},{long2}', mode='driving')['rows'][0]['elements'][0] #Colocando distancia do hub ao primeiro atendimento
                road.iat[EixoXRoad, 15] = consulta['distance']['text'] #colocando a distancia em uma coluna
                road.iat[EixoXRoad, 16] = consulta['duration']['text'] #colocando o tempo de atendimento em outra coluna
                PData = datetime.datetime.combine(date, road.iat[EixoXRoad, 2]) # Define a primeira data para identificar o horário da escala
                qtdAtendimentos = 2 #Deixando a próxima sequencia anotada para a continuação do loop
                EixoXRoad = EixoXRoad + 1 #Deixando o próximo atendimento da sequencia anotada para a continuação do loop

        print(road)
        # ------------------------ COLOCANDO AS AGENDAS ---------------------- #
        # Alimentando a coluna agendas
        while(linhas > calculoAgenda): #Se a quantidade de linhas for maior que o loop de agendas, faça:
            if road.iat[calculoAgenda, 13] == 1: #Se o número do atendimento for 1
                qtdAgendas = qtdAgendas + 1 #Aumenta a quantidade de agendas para 1
                road.iat[calculoAgenda, 14] = qtdAgendas #Coloca essa quantidade de agendas no eixo atual
                calculoAgenda = calculoAgenda + 1 #Aumenta o número para o loop seguir
            elif road.iat[calculoAgenda, 13] - road.iat[calculoAgenda - 1, 13] == 1: #Se o número do atendimento do eixo atual - o atendimento do eixo anterior for igual a 1 faça!
                road.iat[calculoAgenda, 14] = qtdAgendas  #Coloca essa quantidade de agendas no eixo atual
                calculoAgenda = calculoAgenda + 1 #Aumenta o número para o loop seguir

        # ------------------------ ESCALANDO O TIME ( PLACA DO CARRO ) ---------------------- #
        #Escalando a equipe de acordo com a agenda
        while(Capacidade > EscalaReal): #Verifica se a capacidade atual é maior que a variavel EscalaReal
            #Declarando variaveis importantes para esse loop
            HrMin = road[road['Agendas'] == EscalaReal + 1].min() #determina a linha que contém o horário mínimo da agenda do filtro atual
            HrMax = road[road['Agendas'] == EscalaReal + 1].max() #determina a linha que contém o horário máximo da agenda do filtro atual
            HorárioMin = datetime.datetime.combine(date, HrMin['hr_agendamento']) #Pega o horário mínimo da agenda atual
            HorárioMax = datetime.datetime.combine(date, HrMax['hr_agendamento']) #Pega o horário máximo da agenda atual
            
            #Verifica se o horário minimo da agenda é maior que o horário inicial de trabalho da equipe e se o horário maximo é maior que o horário final da equipe e se tem capacidade
            if HorárioMin >= convert(Iniciod6) and HorárioMax <= convert(Fimd6) and d6 != 0:
                PlacaAtual = Placas[(Placas['Código'] == 'd6') & (Placas['Índice'] == d6)] #Filtra o índice e diarista 6 as 12
                road.loc[road.Agendas == EscalaReal + 1,'Placa'] = PlacaAtual.iat[0, 0]#Coloca a placa
                d6 = d6 - 1 #Diminui a quantidade de técnicas diaristas de 6 as 12 disponíveis
                road.loc[road.Agendas == EscalaReal + 1,'Escala']='6 - 12' #Escreve qual é a escala desse time
            #Verifica se o horário minimo da agenda é maior que o horário inicial de trabalho da equipe e se o horário maximo é maior que o horário final da equipe e se tem capacidade
            elif HorárioMin >= convert(Iniciod7) and HorárioMax <= convert(Fimd7) and d7 != 0:
                PlacaAtual = Placas[(Placas['Código'] == 'd7') & (Placas['Índice'] == d7)] #Filtra o índice e diarista 7 as 13
                road.loc[road.Agendas == EscalaReal + 1,'Placa'] = PlacaAtual.iat[0, 0]#Coloca a placa
            #Verifica se o horário minimo da agenda é maior que o horário inicial de trabalho da equipe e se o horário maximo é maior que o horário final da equipe e se tem capacidade
            elif HorárioMin >= convert(Iniciod8) and HorárioMax <= convert(Fimd8) and d8 != 0:
                PlacaAtual = Placas[(Placas['Código'] == 'd8') & (Placas['Índice'] == d8)] #Filtra o índice e diarista 8 as 14
                road.loc[road.Agendas == EscalaReal + 1,'Placa'] = PlacaAtual.iat[0, 0]#Coloca a placa
                d8 = d8 - 1 #Diminui a quantidade de técnicas diaristas de 8 as 14 disponíveis
                road.loc[road.Agendas == EscalaReal + 1,'Escala']='08 - 14' #Escreve qual é a escala desse time
            #Verifica se o horário minimo da agenda é maior que o horário inicial de trabalho da equipe e se o horário maximo é maior que o horário final da equipe e se tem capacidade    
            elif HorárioMin >= convert(Iniciop6) and HorárioMax <= convert(Fimp6) and p6 != 0:
                PlacaAtual = Placas[(Placas['Código'] == 'p6') & (Placas['Índice'] == p6)] #Filtra o índice e plantonista 6 as 18
                road.loc[road.Agendas == EscalaReal + 1,'Placa'] = PlacaAtual.iat[0, 0]#Coloca a placa
                p6 = p6 - 1 #Diminui a quantidade de técnicas plantonistas de 6 as 18 disponíveis
                road.loc[road.Agendas == EscalaReal + 1,'Escala']='6 - 18' #Escreve qual é a escala desse time
            #Verifica se o horário minimo da agenda é maior que o horário inicial de trabalho da equipe e se o horário maximo é maior que o horário final da equipe e se tem capacidade      
            elif HorárioMin >= convert(Iniciop7) and HorárioMax <= convert(Fimp7) and p7 != 0:
                PlacaAtual = Placas[(Placas['Código'] == 'p7') & (Placas['Índice'] == p7)] #Filtra o índice e plantonista 7 as 19
                road.loc[road.Agendas == EscalaReal + 1,'Placa'] = PlacaAtual.iat[0, 0]#Coloca a placa
                p7 = p7 - 1 #Diminui a quantidade de técnicas plantonistas de 7 as 19 disponíveis
                road.loc[road.Agendas == EscalaReal + 1,'Escala']='7 - 19' #Escreve qual é a escala desse time
            else:
                road.loc[road.Agendas == EscalaReal + 1,'Escala']='0' #Se não encontrar nada que se encaixa, fica sem escala
        
            EscalaReal = EscalaReal + 1 #Aumenta a quantidade de EscalaReal para que continue rodando o loop até alocar toda a capacidade

        # ------------------------ CONFIGURANDO O MAPA ---------------------- #
        #Variavel com o tamanho do mapa
        figMapa = Figure(height=600, width=800)
        #Criando o mapa, limpando ele e dando zoom
        mapa = folium.Map(location=[FiltroHubEndereço.iat[0, 3],FiltroHubEndereço.iat[0, 4]], zoom_start=10, tiles='cartodbpositron')
        #Colocando o marcador hub no mapa
        folium.Marker(location=[FiltroHubEndereço.iat[0, 3], FiltroHubEndereço.iat[0, 4]],popup='HUB',icon=folium.Icon(color='lightblue',icon='icon')).add_to(mapa) 
        #Loop para colocar as cores nos marcadores e dados no mapa
        for i in range(0,len(road)):
            html=f"""
                <h2>  Informações: </h2>
                <p><negrito>Agenda:</negrito>{int(road.iloc[i]['Agendas'])}</p>
                <p> Sequência Atendimento: {int(road.iloc[i]['Atendimentos'])}  </p>
                <p> Horário Atendimento: {road.iloc[i]['hr_agendamento']}  </p>
                <p> KM: {road.iloc[i]['KM']}  </p>
                <p> Tempo de Atendimento: {road.iloc[i]['Tempo']}  </p>
                <p> Placa: {road.iloc[i]['Placa']}  </p>
                <p> Escala: {road.iloc[i]['Escala']}  </p>
                <p> Área: {road.iloc[i]['parceiro_nome']}  </p>
                """
            iframe = folium.IFrame(html=html, width=270, height=370)
            popup = folium.Popup(iframe, max_width=420)
            folium.Marker(
                location=[road.iloc[i]['latitude'], road.iloc[i]['longitude']], name=road.iloc[i]['Placa'], popup=popup,
                icon=plugins.BeautifyIcon(
                                icon="arrow-down", icon_shape="marker",
                                number=int(road.iloc[i]['Atendimentos']),
                                text_color='white',
                                border_color=cores.iloc[int(road.iloc[i]['Agendas'])]['Cores'],
                                background_color=cores.iloc[int(road.iloc[i]['Agendas'])]['Cores']
                            )
            ).add_to(mapa)
        #Adicionando controle para remover e colocar agendas no mapa
        folium.LayerControl().add_to(mapa)  
        #Adicionando o tamanho no mapa
        figMapa.add_child(mapa)
        #Salvando o mapa em html
        mapa.save('templates/mapa.html')

        print(road)
        print('Roteirização realizada com SUCESSO!')

        # determining the name of the file
        file_name = 'Road.xlsx'

        # saving the excel
        road.to_excel(file_name)
        print('Salvamos o arquivo em formato excel roteirizado na sua pasta!')