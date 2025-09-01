import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(layout="wide")

# --- CUSTOM FONT + BLACK TEXT ---
st.markdown(
    """
    <style>
    /* Main background */
    .stApp {
        background-color: black;
        color: black;
    }

    /* Sidebar background */
    .css-1d391kg {
        background-color: #111111;
        color: black;
    }

    /* Metric card text */
    .stMetricValue, .stMetricDelta {
        color: black !important;
    }

    /* Card container */
    .card {
        background-color: #111111;
        color: black !important;
    }

    /* Other text elements */
    .stText, .stMarkdown {
        color: black !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- DATA FUNCTIONS ---
def main_df_construct():
    db = sqlite3.connect(r'resto.db')
    df = pd.read_sql("SELECT * FROM Orders", db)
    return df

def filter_df_by_date(df, option):
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M:%S.%f")
    today = datetime.now().date()

    if option == "Aujourd'hui":
        return df[df['time'].dt.date == today]
    elif option == "Hier":
        yesterday = today - timedelta(days=1)
        return df[df['time'].dt.date == yesterday]
    elif option == "Derniers 7 jours":
        week_ago = today - timedelta(days=7)
        return df[df['time'].dt.date >= week_ago]
    elif option == "Derniers 30 jours":
        month_ago = today - timedelta(days=30)
        return df[df['time'].dt.date >= month_ago]
    elif option == "Global":
        return df
    else:
        return df

def deserialize_df(df):
    if df.empty:
        return pd.DataFrame()
    deserialized_content = []
    for items in df['order_content']:
        deserialized_content.extend(json.loads(items))
    return pd.DataFrame(deserialized_content)

def calculate_revenue(df):
    if df.empty:
        return None
    df['total_price'] = df['count'] * df['price']
    return df['total_price'].sum()

def total_orders(df):
    if df.empty:
        return None
    return len(df)

def top_ordered_categories(df):
    if df.empty:
        return pd.Series(dtype=int)
    return df['category'].value_counts()

def total_orders_per_day():
    df = main_df_construct()
    if df.empty:
        return pd.Series(dtype=int)
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M:%S.%f")
    return df['time'].dt.date.value_counts()

def table_orders(df):
    if df.empty:
        return pd.Series(dtype=int)
    return df['table_id'].value_counts()

def waiter_orders(df):
    if df.empty:
        return pd.Series(dtype=int)
    return df['waiter'].value_counts()

def revenue_per_day(df):
    df = main_df_construct()
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M:%S.%f")

    def order_total(order_json_str):
        items = json.loads(order_json_str)
        return sum(item['price'] * item['count'] for item in items)

    df['order_total'] = df['order_content'].apply(order_total)
    daily_revenue = df.groupby(df['time'].dt.date)['order_total'].sum()
    return daily_revenue

# --- FUNCTION TO MAKE AXES WHITE ---
def update_axes_white(fig):
    fig.update_layout(
        xaxis=dict(title_font_color='white', tickfont_color='white'),
        yaxis=dict(title_font_color='white', tickfont_color='white')
    )
    return fig

# --- DASHBOARD ---
st.markdown("<h1 style='text-align:center; color:white;'>🍽️ Tableau de Commandes du Restaurant</h1>", unsafe_allow_html=True)

# --- DATE FILTER DROPDOWN ---
filter_option = st.selectbox(
    "Sélectionnez la période",
    ["Aujourd'hui", "Hier", "Derniers 7 jours", "Derniers 30 jours", "Global"]
)

# --- FILTER AND DESERIALIZE DATA ---
df = main_df_construct()
filtered_df = filter_df_by_date(df, filter_option)
filtered_deserialized_df = deserialize_df(filtered_df)

# --- METRIC CARDS ---
col1, col2 = st.columns(2)
with col1:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    revenue = calculate_revenue(filtered_deserialized_df)
    st.metric("Revenu", f"${revenue:,.2f}" if revenue is not None else "Données non disponibles")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    orders_count = total_orders(filtered_deserialized_df)
    st.metric("Nombre total de commandes", orders_count if orders_count is not None else "Données non disponibles")
    st.markdown("</div>", unsafe_allow_html=True)

# --- ROW 1 (Top Selling Items + Categories) ---
col1, col2 = st.columns(2)
with col1:
    if not filtered_deserialized_df.empty:
        top_items = filtered_deserialized_df.groupby("name")["count"].sum().reset_index().sort_values(by="count", ascending=False)
        fig_items = px.bar(top_items.head(10), x="name", y="count", color="name", title=f"Top 10 Articles Vendus ({filter_option})")
        fig_items.update_layout(showlegend=False)
        fig_items = update_axes_white(fig_items)
        st.plotly_chart(fig_items, use_container_width=True)
    else:
        st.info(f"Aucune donnée de commandes disponible pour {filter_option.lower()}")

with col2:
    top_categories = top_ordered_categories(filtered_deserialized_df)
    if not top_categories.empty:
        fig_cat = px.pie(values=top_categories.values, names=top_categories.index,
                         title=f"Catégories les plus commandées ({filter_option})", hole=0.4)
        fig_cat = update_axes_white(fig_cat)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info(f"Aucune donnée de catégorie disponible pour {filter_option.lower()}")

# --- ROW 2 (Orders Over Time) ---
orders_per_day = total_orders_per_day()
if not orders_per_day.empty:
    orders_per_day = orders_per_day.sort_index()
    fig_orders = px.line(
        x=orders_per_day.index,
        y=orders_per_day.values,
        title="Nombre de commandes par jour"
    )
    fig_orders = update_axes_white(fig_orders)
    st.plotly_chart(fig_orders, use_container_width=True)
else:
    st.info("Aucun historique de commandes disponible")

# --- ROW 3 (Revenue by Category + Items per Category) ---
col1, col2 = st.columns(2)
with col1:
    if not filtered_deserialized_df.empty:
        filtered_deserialized_df["total_price"] = filtered_deserialized_df["count"] * filtered_deserialized_df["price"]
        cat_rev = filtered_deserialized_df.groupby("category")["total_price"].sum().reset_index()
        fig_rev = px.bar(cat_rev, x="category", y="total_price", color="category", title=f"Revenu par catégorie ({filter_option})")
        fig_rev = update_axes_white(fig_rev)
        st.plotly_chart(fig_rev, use_container_width=True)
    else:
        st.info(f"Aucun revenu disponible pour {filter_option.lower()}")

with col2:
    if not filtered_deserialized_df.empty:
        cat_count = filtered_deserialized_df.groupby("category")["count"].sum().reset_index()
        fig_count = px.bar(cat_count, x="category", y="count", color="category", title=f"Articles commandés par catégorie ({filter_option})")
        fig_count = update_axes_white(fig_count)
        st.plotly_chart(fig_count, use_container_width=True)
    else:
        st.info(f"Aucune donnée de catégorie disponible pour {filter_option.lower()}")

# --- ROW 4 (Table & Waiter Stats) ---
col1, col2 = st.columns(2)
with col1:
    table_stats = table_orders(filtered_df)
    if not table_stats.empty:
        fig_table = px.bar(x=table_stats.index, y=table_stats.values,
                           title=f"Commandes par table ({filter_option})", labels={"x": "Table", "y": "Commandes"})
        fig_table = update_axes_white(fig_table)
        st.plotly_chart(fig_table, use_container_width=True)
    else:
        st.info(f"Aucune donnée de table disponible pour {filter_option.lower()}")

with col2:
    waiter_stats = waiter_orders(filtered_df)
    if not waiter_stats.empty:
        fig_waiter = px.bar(x=waiter_stats.index, y=waiter_stats.values,
                            title=f"Commandes par serveur ({filter_option})", labels={"x": "Serveur", "y": "Commandes"})
        fig_waiter = update_axes_white(fig_waiter)
        st.plotly_chart(fig_waiter, use_container_width=True)
    else:
        st.info(f"Aucune donnée de serveur disponible pour {filter_option.lower()}")

daily_revenue = revenue_per_day(df)
if not daily_revenue.empty:
    daily_revenue = daily_revenue.sort_index()
    fig_revenue = px.line(
        x=daily_revenue.index,
        y=daily_revenue.values,
        title="Revenu par jour",
        labels={"x": "Date", "y": "Revenu ($)"}
    )
    fig_revenue.update_yaxes(tickprefix="$")
    fig_revenue = update_axes_white(fig_revenue)
    st.plotly_chart(fig_revenue, use_container_width=True)
else:
    st.info("Aucun revenu disponible")

# --- FOOTER ---
st.markdown("<p style='text-align:center; font-size:14px; color:white;'>Créé avec ❤️ Streamlit + Plotly</p>", unsafe_allow_html=True)




