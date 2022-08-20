import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show table of stocks"""
    user_id = session["user_id"]

    stocks = db.execute("SELECT symbol, name, price, SUM(shares) as totalShares FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
    total = cash
    for stock in stocks:
        total += stock["price"] * stock["totalShares"]

    return render_template("index.html", stocks=stocks, cash = cash, total = total, usd = usd)

    return apology("Error")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    """Buy shares of stock"""

                # create table transactions(
                # id integer primary key autoincrement,
                # user_id integer not null,
                # name text not null,
                # shares integer not null,
                # price numeric not null,
                # type text not null,
                # symbol text not null,
                # time timestamp default current_timestamp,
                # foreign key(user_id) refrences users(id));


    if request.method == "POST":

        symbol = request.form.get("symbol")
        value = lookup(symbol)
         # Ensure number of shares submited
        shares = request.form.get("shares")
        # Ensure symbol was submitted
        if not symbol:
            return apology("must provide symbol")

        elif not value:
            return apology("invalid symbol")

        if not shares:
            return apology("must provide number of shares")
        try:
            shares =int(shares)
        except:
            return apology("must provide valid number of shares")
        if shares <= 0 or (shares % 1) !=0:
            return apology("must provide valid number of shares")

        user_id = session["user_id"]
        cash_available = db.execute("SELECT cash FROM users WHERE id = ?", user_id) [0]["cash"]
        name = value["name"]
        price = value["price"]
        total = price * shares

        if cash_available < total:
            return apology("Not enough cash")
        else:
            db.execute("UPDATE users SET cash = ? WHERE id =?", cash_available - total, user_id)
            db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", user_id, name, shares, price, 'buy', symbol)
            return redirect('/')
    else:
        return render_template("buy.html")

    return apology("Error")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.execute("SELECT type, symbol, price, shares, time FROM transactions WHERE user_id = ? ", user_id,)

    return render_template("history.html", transactions=transactions, usd = usd)

    return apology("Error")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""


    if request.method == "POST":


        if not request.form.get("symbol"):
            return apology("must provide stock symbol")


        quote = lookup(request.form.get("symbol"))


        if quote == None:
            return apology("Stock symbol not valid, please try again")


        else:
            return render_template("quoted.html", quote=quote,usd = usd)


    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation =request.form.get("confirmation")
        # Ensure username was submitted
        if not username :
            return apology("must provide username")

        # Ensure password was submitted
        elif not password :
            return apology("must provide password")

        elif not confirmation:
            return apology("please confirm password")

        if password != confirmation:
            return apology("passwords doesn't match")

        hash= generate_password_hash(password)
        try:


            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)

            return redirect("/")

        except:
            return apology("username is already registered")
    else:
        return render_template("register.html")

    return apology("Error")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        user_id = session["user_id"]
        # Ensure symbol was submitted
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
            return apology("must provide symbol", 403)
        if not shares:
            return apology("must provide number of shares", 403)
        try:
            shares =int(shares)
        except:
            return apology("must provide valid number of shares")
        if shares <= 0 or (shares % 1) !=0:
            return apology("must provide valid number of shares")


        price = lookup(symbol)["price"]
        name = lookup(symbol)["name"]
        total = price * shares
        shares_owned = db.execute("SELECT shares FROM  transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol ", user_id, symbol)[0]["shares"]

        if shares_owned < shares:
            return apology("There's not enough shares")

        cash_available = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        db.execute("UPDATE users SET cash = ? WHERE id =?", cash_available + total, user_id)
        db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)",
                    user_id, name, -shares, price, 'sell', symbol)

        return redirect("")

    else:
        user_id = session["user_id"]
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol", user_id )

        return render_template("sell.html", symbol = symbols)


    return apology("Error")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
