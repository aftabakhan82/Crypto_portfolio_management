from flask import Flask, request, render_template, redirect, url_for,send_file
from flask_sqlalchemy import SQLAlchemy
import requests
import matplotlib
import numpy as np
matplotlib.use('agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import io

app = Flask(__name__,static_url_path='/static', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio.db'
db = SQLAlchemy(app)
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)

@app.route('/')
def index():
    transactions = Transaction.query.all()
    portfolio = []
    live_prices = {}
    for transaction in transactions:
        portfolio.append({
            'id': transaction.id,
            'symbol': transaction.symbol,
            'amount': transaction.amount,
            'price': transaction.price
        })
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={transaction.symbol}USDT'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                live_prices[transaction.symbol] = float(data['price'])
            else:
                live_prices[transaction.symbol] = 0.0  # Fallback for missing price
        else:
            live_prices[transaction.symbol] = 0.0  # Fallback for failed requests
    return render_template('index.html', portfolio=portfolio, live_prices=live_prices)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    symbol = request.form['symbol'].upper()
    amount = float(request.form['amount'])
    price = float(request.form['price'])
    new_transaction = Transaction(symbol=symbol, amount=amount, price=price)
    db.session.add(new_transaction)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/delete_transaction/<int:id>', methods=['POST'])
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/chart')
def chart():
    transactions = Transaction.query.all()
    symbols = [transaction.symbol for transaction in transactions]
    amounts = [transaction.amount for transaction in transactions]

    plt.figure(figsize=(10, 5))
    plt.pie(amounts, labels=symbols, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')
    plt.title('Portfolio Distribution')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return send_file(img, mimetype='image/png')



@app.route('/profit_chart')
def profit_chart():
    transactions = Transaction.query.all()
    live_prices = {}
    for transaction in transactions:
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={transaction.symbol}USDT'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                live_prices[transaction.symbol] = float(data['price'])
            else:
                live_prices[transaction.symbol] = 0.0  # Fallback for missing price
        else:
            live_prices[transaction.symbol] = 0.0  # Fallback for failed requests

    symbols = [transaction.symbol for transaction in transactions]
    profits = [
        (transaction.amount * live_prices.get(transaction.symbol, 0.0)) - (transaction.amount * transaction.price)
        for transaction in transactions
    ]

    plt.figure(figsize=(10, 5))
    bars = plt.bar(symbols, profits)
    plt.xlabel('Symbols')
    plt.ylabel('Profit/Loss')
    plt.title('Profit/Loss Chart')

    for bar in bars:
        bar.set_color('green' if bar.get_height() >= 0 else 'red')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()  # Close the figure after saving it
    return send_file(img, mimetype='image/png')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
