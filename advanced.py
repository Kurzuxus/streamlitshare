import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(layout="wide")

# --- CUSTOM FONT ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Edu+NSW+ACT+Foundation:wght@400;600&display=swap');
    * {
        font-family: 'Edu NSW ACT Foundation', cursive !important;
    }
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- DATA FUNCTIONS ---
def main_df_construct():
    db = sqlite3.connect(r'testing.db')
    df = pd.read_sql("SELECT * FROM Orders", db)
    return df

def filter_df_by_date(df, option):
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M:%S.%f")
    today = datetime.now().date()

    if option == "Today":
        return df[df['time'].dt.date == today]
    elif option == "Yesterday":
        yesterday = today - timedelta(days=1)
        return df[df['time'].dt.date == yesterday]
    elif option == "Last 7 Days":
        week_ago = today - timedelta(days=7)
        return df[df['time'].dt.date >= week_ago]
    elif option == "Last 30 Days":
        month_ago = today - timedelta(days=30)
        return df[df['time'].dt.date >= month_ago]
    elif option == "Overall":
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
    df=main_df_construct()

    df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M:%S.%f")

    def order_total(order_json_str):
        items = json.loads(order_json_str)
        return sum(item['price'] * item['count'] for item in items)

    df['order_total'] = df['order_content'].apply(order_total)

    # Group by date and sum totals
    daily_revenue = df.groupby(df['time'].dt.date)['order_total'].sum()
    return daily_revenue

# --- DASHBOARD ---
st.markdown("<h1 style='text-align:center;'>🍽️ Restaurant Orders Dashboard</h1>", unsafe_allow_html=True)

# --- DATE FILTER DROPDOWN ---
filter_option = st.selectbox(
    "Select Date Range",
    ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "Overall"]
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
    st.metric("Revenue", f"${revenue:,.2f}" if revenue is not None else "Data not available")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    orders_count = total_orders(filtered_deserialized_df)
    st.metric("Total Orders", orders_count if orders_count is not None else "Data not available")
    st.markdown("</div>", unsafe_allow_html=True)

# --- ROW 1 (Top Selling Items + Categories) ---
col1, col2 = st.columns(2)
with col1:
    if not filtered_deserialized_df.empty:
        top_items = filtered_deserialized_df.groupby("name")["count"].sum().reset_index().sort_values(by="count", ascending=False)
        fig_items = px.bar(top_items.head(10), x="name", y="count", color="name", title=f"Top 10 Selling Items ({filter_option})")
        fig_items.update_layout(showlegend=False)
        st.plotly_chart(fig_items, use_container_width=True)
    else:
        st.info(f"No order data available for {filter_option.lower()}")

with col2:
    top_categories = top_ordered_categories(filtered_deserialized_df)
    if not top_categories.empty:
        fig_cat = px.pie(values=top_categories.values, names=top_categories.index,
                         title=f"Top Ordered Categories ({filter_option})", hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info(f"No category data available for {filter_option.lower()}")

# --- ROW 2 (Orders Over Time) ---
orders_per_day = total_orders_per_day()
if not orders_per_day.empty:
    # Sort by date
    orders_per_day = orders_per_day.sort_index()
    
    fig_orders = px.line(
        x=orders_per_day.index,
        y=orders_per_day.values,
        title="Total Orders Per Day"
    )
    fig_orders.update_xaxes(title="Date")
    fig_orders.update_yaxes(title="Orders")
    st.plotly_chart(fig_orders, use_container_width=True)
else:
    st.info("No order history available")

# --- ROW 3 (Revenue by Category + Items per Category) ---
col1, col2 = st.columns(2)
with col1:
    if not filtered_deserialized_df.empty:
        filtered_deserialized_df["total_price"] = filtered_deserialized_df["count"] * filtered_deserialized_df["price"]
        cat_rev = filtered_deserialized_df.groupby("category")["total_price"].sum().reset_index()
        fig_rev = px.bar(cat_rev, x="category", y="total_price", color="category", title=f"Revenue by Category ({filter_option})")
        st.plotly_chart(fig_rev, use_container_width=True)
    else:
        st.info(f"No revenue data available for {filter_option.lower()}")

with col2:
    if not filtered_deserialized_df.empty:
        cat_count = filtered_deserialized_df.groupby("category")["count"].sum().reset_index()
        fig_count = px.bar(cat_count, x="category", y="count", color="category", title=f"Items Ordered Per Category ({filter_option})")
        st.plotly_chart(fig_count, use_container_width=True)
    else:
        st.info(f"No category data available for {filter_option.lower()}")

# --- ROW 4 (Table & Waiter Stats) ---
col1, col2 = st.columns(2)
with col1:
    table_stats = table_orders(filtered_df)
    if not table_stats.empty:
        fig_table = px.bar(x=table_stats.index, y=table_stats.values,
                           title=f"Orders by Table ({filter_option})", labels={"x": "Table", "y": "Orders"})
        st.plotly_chart(fig_table, use_container_width=True)
    else:
        st.info(f"No table data available for {filter_option.lower()}")

with col2:
    waiter_stats = waiter_orders(filtered_df)
    if not waiter_stats.empty:
        fig_waiter = px.bar(x=waiter_stats.index, y=waiter_stats.values,
                            title=f"Orders by Waiter ({filter_option})", labels={"x": "Waiter", "y": "Orders"})
        st.plotly_chart(fig_waiter, use_container_width=True)
    else:
        st.info(f"No waiter data available for {filter_option.lower()}")

daily_revenue = revenue_per_day(df)

if not daily_revenue.empty:
    # Sort by date to ensure chronological order
    daily_revenue = daily_revenue.sort_index()
    
    fig_revenue = px.line(
        x=daily_revenue.index,
        y=daily_revenue.values,
        title="Revenue Per Day",
        labels={"x": "Date", "y": "Revenue ($)"}
    )
    fig_revenue.update_yaxes(tickprefix="$")
    st.plotly_chart(fig_revenue, use_container_width=True)
else:
    st.info("No revenue data available")

# --- FOOTER ---
st.markdown("<p style='text-align:center; font-size:14px;'>Built with ❤️ Streamlit + Plotly</p>", unsafe_allow_html=True)
