import streamlit as st
from datetime import datetime, timedelta
import random
#import urllib.parse
from sqlalchemy.sql import text
import math
import smtplib
from email.mime.text import MIMEText
#from functions.utils import display_cart_part2

USERS = st.secrets['USERS'] #os.getenv('USERS')
USERS = USERS.replace('\n', '')

SELLERS = st.secrets["SELLERS"]

RATES = st.secrets['rates']

if "print_chek" not in st.session_state:
    st.session_state["print_chek"] = False

if "promo_activated" not in st.session_state:
    st.session_state["promo_activated"] = False

st.set_page_config(page_title="Оплата", page_icon="💳", layout="centered")

def dec(s):
    if not s:
        return ""
    
    result = []
    i = 0
    
    while i < len(s):
        result.append(s[i])

        if s[i].isalpha() or s[i].isdigit():
            i += 2 
        else:
            i += 1
    
    return ''.join(result)

def convert_currency2(amount, from_currency, to_currency):
    if from_currency == to_currency:
        return amount
    amount_in_target = amount * RATES[to_currency] / RATES[from_currency] 
    return math.ceil(amount_in_target*100)/100
    #return amount_in_target

# Отображение корзины по частям
def display_cart_part2(cart, cur, conditions, extra_sale_coef):
    sellers = {}
    chek_lines = []
    chek_lines2 = []

    if not cart:
        return None, 0
    #st.subheader(f"Корзина для оплаты {cur}")

    # st.write(extra_sale_coef)
    total_customer = 0
    for pid, qty in cart.items():
        if qty == 0:
            continue
        # находим продукт
        if "_paper" in pid or "_e" in pid:
            base, vtype = pid.split("_")
            prod = next(p for p in products if str(p["id"])==base)
            name = f"{prod['name']} ({'бумажная' if vtype=='paper' else 'электронная'})"
            brand = prod['brand']
        else:
            base = pid
            prod = next(p for p in products if str(p["id"])==pid)
            name = prod["name"]
            brand = prod['brand']

        seller_id = str(pid)[1:3]   
        sh_id = str(pid)[0]
        seller_info = next(s for s in SELLERS if str(s["id"])==seller_id)

        seller_card_no = seller_info["card_no"]

        if seller_card_no[4:7] in ['127', '338']:
            seller_cur = 'BON'
        elif seller_card_no[4:7] in ['253']:
            seller_cur = prod['price']['MUL_cur']
        else: #классические карты
            seller_cur = 'NSN'


        #Если промокод
        if conditions:
            counter = 0
            fulfilled = 0
            if 'brand' in conditions:
                counter += 1
                if conditions['brand'] == brand:
                    fulfilled += 1
                # else:
                #     fulfilled += 0
            if 'seller_id' in conditions:
                counter += 1
                if str(conditions['seller_id']) == str(pid)[1:3]:
                    fulfilled += 1
            if 'excluded_items' in conditions:
                counter += 1
                if int(base) not in conditions['excluded_items']:
                    fulfilled += 1
            if 'included_items' in conditions:
                counter += 1
                if int(base) in conditions['included_items']:
                    fulfilled += 1
            if 'expiration_day' in conditions:
                    counter += 1
                    cur_time = datetime.utcnow() + timedelta(hours=st.secrets['hours'])
                    cur_day = cur_time.date()
                    last_day = datetime.strptime(conditions['expiration_day'], "%Y-%m-%d").date()
                    if cur_day <= last_day:
                        fulfilled += 1          

            if counter == fulfilled:
                # st.write("Промокод применён")
                extra_sale_for_item = extra_sale_coef
            else:
                # st.write(f"Выполнено {fulfilled}/{counter} условий")
                extra_sale_for_item = {'MUL': 1, 'NSN': 1, 'BON': 1}
        else:
            # Не введён промокод
            extra_sale_for_item = {'MUL': 1, 'NSN': 1, 'BON': 1}
        # st.write(extra_sale_for_item)

        #ctype = get_currency_type(prod["id"])
        #if ctype == 1:
        if cur != "NSN" and cur != "BON":
            #unit_price = prod["price"]["MUL"]
            unit_price = convert_currency2(extra_sale_for_item["MUL"] * prod["sale_coef"]["MUL"] * prod["price"]["MUL"], 
                                            prod["price"]["MUL_cur"], 
                                            cur)
            sym = cur
        else:
            unit_price = math.ceil(extra_sale_for_item[cur] * prod["sale_coef"][cur] * prod["price"][cur])
            sym = cur

        if seller_cur != "NSN" and seller_cur != "BON":

            unit_price_without_promo = prod["sale_coef"]["MUL"] * prod["price"]["MUL"]
                                            # convert_currency2(prod["sale_coef"]["MUL"] * prod["price"]["MUL"], 
                                            # prod["price"]["MUL_cur"], 
                                            # cur) 
                                        #промокод оплачивается сазоном, а 
                                        #продавец получает полную сумму
                                        #(но скидка продавца вычитает сумму из его денег)
        else:
            unit_price_without_promo = math.ceil(prod["sale_coef"][seller_cur] * prod["price"][seller_cur])

        unit_price = round(unit_price, 2)
        unit_price_without_promo = round(unit_price_without_promo, 2)
        # elif ctype == 2:
        #     unit_price = prod["price"]
        #     sym = "❤️"
        # else:
        #     unit_price = prod["price"]
        #     sym = "💧"

        line_total = unit_price * qty
        line_total_for_seller = unit_price_without_promo * qty
        total_customer += line_total

        if line_total != line_total_for_seller:
            st.session_state["promo_activated"] = True


        # col_name, col_qty = st.columns([3,0.6])
        # with col_name:
        chek_lines.append(f"{name}")
        chek_lines2.append(f"{name} — {unit_price} {sym} (продавец {seller_id} получит {line_total_for_seller} {seller_cur} на карту {11*'*'}{seller_card_no[11:]})")
        # st.write(f"{name} — {unit_price} {sym} (продавец {seller_id} получит {line_total_for_seller} {seller_cur} на карту {11*'*'}{seller_card_no[11:]})")


        # with col_qty:
        #     st.text_input("", value=str(cart[pid]),
        #                 key=f"qty_{pid}", disabled=True, label_visibility="collapsed")


        if qty > 0:
            chek_lines.append(f"{qty} × {unit_price} {sym} = {line_total} {sym}")
            chek_lines.append(30*'-')
            chek_lines2.append(f"{qty} × {unit_price} {sym} = {line_total} {sym}")
            chek_lines2.append(30*'-')
            #st.write(f"{qty} × {unit_price} {sym} = {line_total} {sym}")
            #st.markdown("---")

        if seller_id in sellers.keys():
            sellers[f'{seller_id}_{seller_cur}'] += line_total_for_seller
        else:
            sellers[f'{seller_id}_{seller_cur}'] = line_total_for_seller

    #округление
    total_customer = round(total_customer, 2)
    for k, v in sellers.items():
        sellers[k] = round(v, 2)

    # st.write(sellers)
    # st.write(total_customer)

    st.subheader(f"ИТОГО К ОПЛАТЕ: {total_customer} {cur}")
    chek_lines.append(f"ИТОГО: {total_customer} {cur}")
    chek_lines.append(30*'-')
    chek_lines2.append(f"ИТОГО: {total_customer} {cur}")
    chek_lines2.append(30*'-')
    st.markdown("---")

    return total_customer, sellers, chek_lines, sh_id, chek_lines2


def int_float_calc(balance_int: int, balance_cents: int, amount: float):
    """
    balance_int, balance_cents  — текущее состояние счёта (0 <= balance_cents < 100)
    amount                      — положительная (пополнение) или отрицательная (списание) сумма,
                                   с точностью до 2 знаков после точки.
    Возвращает (new_int, new_cents) в том же формате.
    """
    # переводим amount в "центовые" единицы
    amount_cents = int(round(amount * 100))

    # складываем всё в одну переменную
    total_cents = balance_int * 100 + balance_cents + amount_cents

    # обратно разбиваем на целые рубли (demand) и центы
    new_balance_int = total_cents // 100
    new_balance_cents = total_cents % 100
    return new_balance_int, new_balance_cents


def upd(balance_name, cents_name, new_balance_int, new_balance_cents, card):

    if cents_name is None:
        cents_balance_upd = ''
    else: 
        cents_balance_upd = f', {cents_name} = {new_balance_cents}'

    with conn.session as s:
        task = f'''UPDATE cards
            SET
                {balance_name} = {new_balance_int}
                {cents_balance_upd}
            WHERE card_no = {card};
            '''
        s.execute(text(task), 
        #ttl="10m",
        )
    
        s.commit()

def get_card_info(conn, card_no):
    # # Perform query.
    df_user = conn.query('SELECT * FROM cards WHERE card_no = :card_no;', 
                    show_spinner="Настройка безопасного соединения...",
                    ttl=0,#None, #"10m",
                    params={"card_no": card_no},)
    #st.write(df)
    return df_user

def payment(cur, total_amount, df):
    '''
    total_amount < 0 : покупатель платит (есть условие, что денег на счёте должно хватать)
    total_amount > 0 : продавец получает (нет условий)
    '''

    if cur == "NSN":
        if df['currency'][0] == "NSN":
            balance_col = 'balance'
        else:
            st.error(f"Не удалось оплатить. Среди валют вашей карты нет валюты {cur}, выбранной для оплаты")
            st.stop()

    elif cur == "BON":
        if df['currency_3'][0] == "BON":
            balance_col = 'third_balance'
        else: 
            st.error(f"Не удалось оплатить. Среди валют вашей карты нет валюты {cur}, выбранной для оплаты")
            st.stop()

    else: # multi
        curs_1 =  [df["currency"][0], df["currency_2"][0], df["currency_3"][0]]
        if cur in curs_1:
            if cur == curs_1[0]:
                balance_col = 'balance'
                cents_col = 'cents_1'
            elif cur == curs_1[1]:
                balance_col = 'second_balance'
                cents_col = 'cents_2'
            elif cur == curs_1[2]:    
                balance_col = 'third_balance'
                cents_col = 'cents_3'
        else:
            st.error(f"Не удалось оплатить. Среди валют вашей карты нет валюты {cur}, выбранной для оплаты")
            st.stop()
            #if df['balance'][0] >= total_amount:

    condition = False
    if total_amount < 0: #user pays money
        if cur == 'NSN' or cur == 'BON':
            total_available = df[balance_col][0]
        else:
            total_available = df[balance_col][0]+df[cents_col][0]/100

        if total_available >= abs(total_amount):
            condition = True
        else:
            st.error("На счёте недостаточно средств для оплаты")
            st.stop()


    if condition==True or total_amount > 0:
        if cur != 'NSN' and cur != 'BON':
            pass # оплата с центами
            new_bal, new_cents = int_float_calc(df[balance_col][0], df[cents_col][0], total_amount)
            #st.write(new_bal)
            #st.write(new_cents)
            upd(balance_col, cents_col, new_bal, new_cents, df['card_no'][0])
        else:
            pass # ОПЛАТА В INT
            new_bal = int(df[balance_col][0] + total_amount)
            #st.write(new_bal)
            upd(balance_col, None, new_bal, None, df['card_no'][0])
    else:
        st.error(f"Ошибка : {condition} {total_amount}")

def send_msg(msg_body, subject=""):
    try:
        #body = "\n".join(chek_lines)
        msg = MIMEText(msg_body)
        msg['From'] = st.secrets["sender"]
        msg['To'] = st.secrets["receiver"]
        msg['Subject'] = subject #f"Заказ {order_number} от {order_date_local}" 

        server = smtplib.SMTP(st.secrets["server"], st.secrets["port"])
        server.starttls()
        server.login(st.secrets["sender"], st.secrets["password"])
        server.sendmail(st.secrets["sender"], st.secrets["receiver"], msg.as_string())
        server.quit()

        #st.success('Email sent successfully! 🚀')
    except Exception as e:
        st.error(f"Failed to send email: {e}")


# ------------------------------------------------------------------
# 1. Загрузка товаров из secrets.toml (только id, name, price)
# ------------------------------------------------------------------
products = st.secrets["products"]  # список словарей
promos = st.secrets["promos"]
SHOPS = st.secrets["SHOPS"]

STREETS = st.secrets['STREETS']
CITIES = st.secrets['CITIES']
COUNTRIES = st.secrets['COUNTRIES']
PLACES = st.secrets['PLACES']
POST_SERVICES = st.secrets['POST_SERVICES']

#st.write(products)


# ------------------------------------------------------------------
# 2. Чтение параметров из URL
# ------------------------------------------------------------------
cart_str = st.query_params.get("cart", "")
time = st.query_params.get("time", "")
if time != "":
    time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")  #приходит в utc
    time_condition = True
else: 
    time_condition = False
#st.write(time)

addr_1_ind = st.query_params.get("addr_1", "")
if addr_1_ind.isdigit():
    if int(addr_1_ind) < len(COUNTRIES):
        addr_1 = COUNTRIES[int(addr_1_ind)]
    else: 
        addr_1 = ""
else: 
    addr_1 = dec(addr_1_ind)

addr_2_ind = st.query_params.get("addr_2", "")
if addr_2_ind.isdigit():
    if int(addr_2_ind) < len(CITIES):
        addr_2 = CITIES[int(addr_2_ind)]
    else: 
        addr_2 = ""
else: 
    addr_2 = dec(addr_2_ind)

addr_3_ind = st.query_params.get("addr_3", "")
if addr_3_ind.isdigit():
    if int(addr_3_ind) < len(STREETS):
        addr_3 = STREETS[int(addr_3_ind)]
    else: 
        addr_3 = ""
else: 
    addr_3 = dec(addr_3_ind)

addr_4_ind = st.query_params.get("addr_4", "")
if addr_4_ind in PLACES.keys():
        addr_4 = PLACES[int(addr_4_ind)]
else: 
    addr_4 = dec(addr_4_ind)

addr_5_ind = st.query_params.get("addr_5", "")
if addr_5_ind.isdigit():
    addr_5 = addr_5_ind + " этаж"
else:
    addr_5 = addr_5_ind

post_serv_ind = st.query_params.get("post", "")
if post_serv_ind != "":
    post_serv = next(ps for ps in POST_SERVICES if str(ps["id"])==post_serv_ind)
    post_serv_name = post_serv['name']
else: 
    post_serv_name = post_serv_ind

word = st.query_params.get("word", "")
cur = st.query_params.get("cur", "")
user_id = st.query_params.get("user_id", "")
user_name = dec(st.query_params.get("name", ""))

address = ""
for i in [addr_1, addr_2, addr_3, addr_4, addr_5]:
    if i != "":
        address += i + ', '
address = address[0: -2] 

# st.write(address)
# st.write(user_name)
# st.write(post_serv_name)


if not cart_str:
    st.error("❌ Данные о заказе не получены.")
    st.stop()

if not word:
    conditions = None
    extra_sale_coef = 1

# ------------------------------------------------------------------
# 3. Преобразуем строку "id,qty;id_e,qty;id_paper,qty;..." в dict
# ------------------------------------------------------------------
cart = {}
for item in cart_str.split(";"):
    if not item:
        continue
    pid, qty = item.split(",")
    cart[pid] = int(qty)
# st.write(cart)


conditions = None
extra_sale_coef = {'MUL': 1, 'NSN': 1, 'BON': 1}
for promo in promos:
    if word == promo["word"]:
        # st.write("Промокод существует")
        # for k, v in promo["conditions"].items():
            # st.write(f"{k} === {v}")
        conditions = promo["conditions"]
        extra_sale_coef = promo["extra_sale_coef"]

total_user, sellers, chek_lines, sh_id, chek_lines2 = display_cart_part2(cart, cur, conditions, extra_sale_coef)



st.title("💳 Оплата")
st.subheader("Введите данные карты")

#st.session_state.card_no
card_number = st.text_input(":blue[Номер карты]", key="card_number_input")

st.caption(":blue[Срок действия]", help=st.secrets['help_line'])
with st.container(horizontal=True, vertical_alignment="bottom", width=500):
    expiry1 = st.text_input("a", key="expiry1_input", placeholder="ММ", max_chars=2, label_visibility="hidden", width=100)

    st.text("/")

    expiry2 = st.text_input("b", key="expiry2_input", placeholder="ГГ", max_chars=2, label_visibility="hidden", width=100)
st.write("")
verif_code = st.text_input(":blue[Смешарик-код]", type="password", key="cvv_input")

# ------------------------------------------------------------------
# 4. Обработчик кнопки «Оплатить»
# ------------------------------------------------------------------
if st.button("Оплатить"):
    if not (card_number and expiry1 and expiry2 and verif_code):
        st.warning("Заполните все поля карты.")
        st.stop()

    if f"{card_number}_{verif_code}" in USERS.split(","):

        st.write("Карта существует")

        order_number = random.randint(100000, 999999)
        order_date_utc = datetime.utcnow()
        
        order_date_local = order_date_utc + timedelta(st.secrets['tzs']['HOURS'])
        
        if time_condition: #user needs to pay in ... minutes
            if (order_date_utc-time).total_seconds() // 60 <= st.secrets['CLEANUP_TIME_IN_MINUTES']:

                # conn = st.connection("neon", type="sql")

                # # Perform query.
                # df = get_card_info(conn, card_number)

                # st.write(df)

                # payment(cur, -total_user, df)

                # for seller_id_cur in sellers.keys():

                #     seller_id = seller_id_cur.split("_")[0]
                #     seller_cur = seller_id_cur.split("_")[1]
                #     seller_info = next(s for s in SELLERS if str(s["id"])==seller_id)
                #     seller_card_no = seller_info["card_no"]


                #     df1 = get_card_info(conn, seller_card_no)

                #     st.write(df1)
                    
                #     payment(seller_cur, +sellers[seller_id_cur], df1)
                st.success("✅ Оплата прошла успешно!!!")

                st.session_state["print_chek"] = True
            else: 
                st.write("Время для оплаты истекло. Вернитесь в магазин и оформите новый заказ")
        else: 
            pass
            #st.write("Сценарий для перевода через qr") 
    else:
        st.write("Пользователь не найден")




if st.session_state["print_chek"]:

    st.subheader("🧾 Чек")

    chek_lines.append(f"Номер заказа: {order_number}")
    chek_lines.append(f"Дата: {order_date_local.strftime('%d.%m.%Y %H:%M:%S')}")
    chek_lines.append(f"Покупатель: {user_name}")
    chek_lines.append(f"Адрес доставки: {address}")
    chek_lines.append(f"Служба доставки: {post_serv_name}")
    chek_lines2.append(f"Номер заказа: {order_number}")
    chek_lines2.append(f"Дата: {order_date_local.strftime('%d.%m.%Y %H:%M:%S')}")
    chek_lines2.append(f"Покупатель: {user_name}")
    chek_lines2.append(f"Адрес доставки: {address}")
    chek_lines2.append(f"Служба доставки: {post_serv_name}")
    # st.markdown("---")
    if st.session_state["promo_activated"] == True: 
        chek_lines.append(f"Использован промокод: {word}")
        chek_lines2.append(f"Использован промокод: {word}")

    with st.expander(f"Заказ {order_number}"):
        for line in chek_lines:
            st.write(line)


    #st.write("отправка на email")
    body = "\n".join(chek_lines2)
    send_msg(body, subject=f"Заказ {order_number} от {order_date_local}")

    sh = next(s for s in SHOPS if str(s["id"])==str(sh_id))
    endpoint = sh["name"]
    link = f"{endpoint}?id={user_id}&o_id={order_number}"
    st.link_button("ВЕРНУТЬСЯ В МАГАЗИН. ***Нажмите для корректного завершения оплаты!!!***", url=link)
    st.caption("Иначе магазин не сможет подтвердить заказ")
