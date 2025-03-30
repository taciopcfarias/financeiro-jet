from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Necessário para usar sessões
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///registros.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo para armazenar os aluguéis
class Aluguel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Float, nullable=False)
    metodo_pagamento = db.Column(db.String(50), nullable=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Se o formulário de seleção de data foi enviado
        if 'data_dia' in request.form:
            session['data_dia'] = request.form['data_dia']
            return redirect(url_for('index'))
        # Se o formulário de lançamento de aluguel foi enviado
        elif 'valor' in request.form and 'metodo_pagamento' in request.form:
            data_str = session.get('data_dia', datetime.today().strftime('%Y-%m-%d'))
            # Converte para objeto date (apenas a data, sem horário)
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
            try:
                valor = float(request.form['valor'])
            except ValueError:
                valor = 0
            metodo_pagamento = request.form['metodo_pagamento']
            novo_aluguel = Aluguel(data=data, valor=valor, metodo_pagamento=metodo_pagamento)
            db.session.add(novo_aluguel)
            db.session.commit()
            return redirect(url_for('index'))
        else:
            # Caso não tenha nenhum dos campos esperados, redireciona para a página principal
            return redirect(url_for('index'))
    else:
        # Para requisições GET: recupera a data selecionada ou utiliza a data de hoje
        data_dia = session.get('data_dia', datetime.today().strftime('%Y-%m-%d'))
        data_obj = datetime.strptime(data_dia, '%Y-%m-%d').date()
        
        # Consulta todos os lançamentos do dia, comparando apenas a parte da data
        alugueis = Aluguel.query.filter(db.func.date(Aluguel.data) == data_obj)\
                                .order_by(Aluguel.id.desc()).all()
        
        # Calcula o total do dia
        total_geral = db.session.query(
            db.func.sum(Aluguel.valor)
        ).filter(db.func.date(Aluguel.data) == data_obj).scalar() or 0

        # Calcula o total em dinheiro para o dia (filtrando pelo método "Dinheiro")
        total_dinheiro = db.session.query(
        db.func.sum(Aluguel.valor)
        ).filter(
        Aluguel.metodo_pagamento == 'Dinheiro'
        ).scalar() or 0
        
        # Calcula o total do mês: extrai o mês e ano da data selecionada (formato 'YYYY-MM')
        data_mes = data_obj.strftime('%Y-%m')
        total_mensal = db.session.query(
            db.func.sum(Aluguel.valor)
        ).filter(db.func.strftime('%Y-%m', Aluguel.data) == data_mes).scalar() or 0
        
        # Consulta os totais por método de pagamento para o dia (opcional)
        totais = db.session.query(
            Aluguel.metodo_pagamento,
            db.func.sum(Aluguel.valor).label('total'),
            db.func.count(Aluguel.id).label('qtd')
        ).filter(db.func.date(Aluguel.data) == data_obj)\
         .group_by(Aluguel.metodo_pagamento).all()
        
        return render_template('index.html',
                               data_dia=data_dia,
                               alugueis=alugueis,
                               total_geral=total_geral,
                               total_mensal=total_mensal,
                               total_dinheiro=total_dinheiro,
                               totais=totais)

@app.route('/filtrar', methods=['GET'])
def filtrar():
    data_inicial_str = request.args.get('data_inicial')
    data_final_str = request.args.get('data_final')
    
    if not data_inicial_str or not data_final_str:
        return redirect(url_for('index'))
    
    data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
    data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
    
    registros_filtrados = Aluguel.query.filter(
        Aluguel.data >= data_inicial,
        Aluguel.data <= data_final
    ).order_by(Aluguel.data.desc()).all()
    
    total_filtrado = db.session.query(
        db.func.sum(Aluguel.valor)
    ).filter(
        Aluguel.data >= data_inicial,
        Aluguel.data <= data_final
    ).scalar() or 0
    
    return render_template('filtrar.html',
                           registros_filtrados=registros_filtrados,
                           total_filtrado=total_filtrado,
                           data_inicial=data_inicial_str,
                           data_final=data_final_str)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
