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
                for item in items[:20]:  # Показываем только первые 20 результатов
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
        # Фильтры
        min_price_watched = st.slider("Минимальная цена (₽)", 0, 10000, 0, key="min_price_watched")
        max_price_watched = st.slider("Максимальная цена (₽)", 0, 10000, 10000, key="max_price_watched")

        for item_name in watched_items:
            item_data = data_manager.watched_items[item_name]
            current_price_data = steam_api.get_item_price(item_name)

            if current_price_data and 'lowest_price' in current_price_data:
                current_price = steam_api._parse_price(current_price_data['lowest_price'])

                # Применяем фильтры
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

                # График цен
                if item_data['price_history']:
                    dates = [datetime.fromisoformat(date) for date, _ in item_data['price_history']]
                    prices = [price for _, price in item_data['price_history']]

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

    # Настройки поиска
    col1, col2, col3 = st.columns(3)
    with col1:
        min_profit = st.slider("Минимальная прибыль (%)", 1, 100, 3)
    with col2:
        category_filter = st.selectbox(
            "Категория предметов",
            ["Все", "Редкие предметы", "Обычные предметы"]
        )
    with col3:
        max_items = st.number_input("Количество предметов для анализа", 100, 1000, 500)

    # Дополнительные фильтры
    show_filters = st.checkbox("Показать дополнительные фильтры")
    if show_filters:
        col1, col2, col3 = st.columns(3)
        with col1:
            min_price = st.number_input("Минимальная цена (₽)", 0, 10000, 0)
        with col2:
            max_price = st.number_input("Максимальная цена (₽)", 0, 100000, 100000)
        with col3:
            min_volume = st.number_input("Минимальный объем продаж", 1, 1000, 3)

    if st.button("🔄 Найти выгодные предметы"):
        with st.spinner("Анализ рынка... Это может занять некоторое время"):
            profitable_items = steam_api.find_profitable_items(min_profit, max_items)

            if profitable_items:
                # Применяем фильтры
                filtered_items = [
                    item for item in profitable_items
                    if (
                        (not show_filters or
                         (min_price <= item['current_price'] <= max_price and
                          item['volume'] >= min_volume)) and
                        (category_filter == "Все" or
                         (category_filter == "Редкие предметы" and item['category'] == "Rare") or
                         (category_filter == "Обычные предметы" and item['category'] == "Common"))
                    )
                ]

                if filtered_items:
                    st.success(f"Найдено {len(filtered_items)} выгодных предложений!")

                    # Показываем статистику
                    df = pd.DataFrame(filtered_items)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Средняя прибыль", f"{df['profit_percent'].mean():.1f}%")
                    with col2:
                        st.metric("Средний объем продаж", f"{df['volume'].mean():.0f}")
                    with col3:
                        st.metric("Средняя волатильность", f"{df['volatility'].mean():.1f}%")
                    with col4:
                        st.metric("Активных продаж", f"{df['sell_listings'].mean():.0f}")

                    # Показываем каждый предмет
                    for item in filtered_items:
                        with st.container():
                            st.write("---")
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                            with col1:
                                st.write(f"**{item['name']}**")
                                st.write(f"Категория: {item['category']}")
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
                    st.warning(
                        "Нет предметов, соответствующих выбранным критериям. "
                        "Попробуйте изменить фильтры или категорию предметов."
                    )
            else:
                st.warning(
                    "Выгодных предложений не найдено. "
                    "Попробуйте уменьшить минимальную прибыль или увеличить количество анализируемых предметов."
                )

# Обновление цен
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