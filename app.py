import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from steam_api import SteamMarketAPI
from data_manager import DataManager
import pandas as pd

# Инициализация
steam_api = SteamMarketAPI()
data_manager = DataManager()

# Настройка страницы
st.set_page_config(
    page_title="Отслеживание цен Steam",
    page_icon="📈",
    layout="wide"
)

# Заголовок
st.title("📈 Анализатор цен Steam Market")

# Создаем вкладки
tab1, tab2 = st.tabs(["🔍 Поиск предметов", "💰 Выгодные предложения"])

with tab1:
    # Поиск предметов
    search_query = st.text_input("🔍 Поиск предметов", key="search")
    if search_query:
        with st.spinner("Поиск предметов..."):
            items = steam_api.search_items(search_query)
            if items:
                st.subheader("Результаты поиска")
                for item in items:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.write(item['name'])
                    with col2:
                        st.write(f"Цена: {item.get('price', 'Н/Д')} ₽")
                    with col3:
                        if st.button("Отслеживать", key=f"watch_{item['name']}"):
                            price = steam_api._parse_price(item.get('price', '0'))
                            data_manager.add_watched_item(item['name'], price)
                            st.success("Предмет добавлен в отслеживаемые!")
                            st.rerun()
            else:
                st.warning("Ничего не найдено")

    # Отслеживаемые предметы
    st.subheader("📋 Отслеживаемые предметы")
    watched_items = data_manager.get_watched_items()

    if not watched_items:
        st.info("У вас пока нет отслеживаемых предметов")
    else:
        # Фильтры (unchanged from original)
        min_price_watched = st.slider("Минимальная цена (₽)", 0, 10000, 0, key="min_price_watched")
        max_price_watched = st.slider("Максимальная цена (₽)", 0, 10000, 10000, key="max_price_watched")

        for item_name in watched_items:
            item_data = data_manager.watched_items[item_name]
            current_price_data = steam_api.get_item_price(item_name)

            if current_price_data and 'lowest_price' in current_price_data:
                current_price = steam_api._parse_price(current_price_data['lowest_price'])

                # Применяем фильтры (unchanged from original)
                if current_price < min_price_watched or current_price > max_price_watched:
                    continue

                st.write("---")
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    st.write(f"**{item_name}**")
                with col2:
                    price_diff = current_price - item_data['initial_price']
                    price_diff_percent = (price_diff / item_data['initial_price']) * 100

                    st.write(f"Текущая цена: {current_price:.2f} ₽")
                    st.write(f"Изменение: {price_diff_percent:+.2f}%")
                with col3:
                    if st.button("Удалить", key=f"remove_{item_name}"):
                        data_manager.remove_watched_item(item_name)
                        st.rerun()

                # График цен (unchanged from original)
                price_history = item_data['price_history']
                if price_history:
                    dates = [datetime.fromisoformat(date) for date, _ in price_history]
                    prices = [price for _, price in price_history]

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=prices,
                        mode='lines+markers',
                        name='Цена'
                    ))

                    fig.update_layout(
                        title=f"История цен: {item_name}",
                        xaxis_title="Дата",
                        yaxis_title="Цена (₽)",
                        height=400
                    )

                    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("💰 Выгодные предложения для перепродажи")

    # Настройки поиска (modified from edited)
    col1, col2, col3 = st.columns(3)
    with col1:
        min_profit = st.slider("Минимальная прибыль (%)", 1, 100, 5)
    with col2:
        min_volume = st.number_input("Минимальный объем продаж", 1, 1000, 10)
    with col3:
        max_items = st.number_input("Количество предметов для анализа", 100, 1000, 500)

    if st.button("🔄 Найти выгодные предметы"):
        with st.spinner("Анализ рынка... Это может занять некоторое время"):
            profitable_items = steam_api.find_profitable_items(min_profit, max_items)

            if profitable_items:
                # Фильтруем по объему продаж (modified from edited)
                filtered_items = [
                    item for item in profitable_items
                    if item['volume'] >= min_volume
                ]

                if filtered_items:
                    st.success(f"Найдено {len(filtered_items)} выгодных предложений!")

                    # Показываем статистику (modified from edited)
                    df = pd.DataFrame(filtered_items)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Средняя прибыль", f"{df['profit_percent'].mean():.1f}%")
                    with col2:
                        st.metric("Средний объем продаж", f"{df['volume'].mean():.0f}")
                    with col3:
                        st.metric("Средняя волатильность", f"{df['volatility'].mean():.1f}%")

                    # Показываем каждый предмет (modified from edited)
                    for item in filtered_items:
                        with st.container():
                            st.write("---")
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                            with col1:
                                st.write(f"**{item['name']}**")
                            with col2:
                                st.write(f"Текущая цена: {item['current_price']:.2f} ₽")
                                st.write(f"Медианная цена: {item['median_price']:.2f} ₽")
                            with col3:
                                st.write(f"Прибыль: {item['profit_percent']:.1f}%")
                                st.write(f"Объем продаж: {item['volume']}")
                            with col4:
                                if st.button("Отслеживать", key=f"watch_profitable_{item['name']}"):
                                    data_manager.add_watched_item(item['name'], item['current_price'])
                                    st.success("Предмет добавлен в отслеживаемые!")
                                    st.rerun()
                else:
                    st.warning("Нет предметов, соответствующих выбранным критериям. Попробуйте уменьшить минимальный объем продаж.")
            else:
                st.warning("Выгодных предложений не найдено. Попробуйте увеличить количество анализируемых предметов.")

# Обновление цен (unchanged from original, but with price parsing improvement)
if watched_items:
    if st.button("🔄 Обновить все цены"):
        with st.spinner("Обновление цен..."):
            for item_name in watched_items:
                price_data = steam_api.get_item_price(item_name)
                if price_data and 'lowest_price' in price_data:
                    current_price = steam_api._parse_price(price_data['lowest_price'])
                    data_manager.update_price(item_name, current_price)
        st.success("Цены обновлены!")
        st.rerun()