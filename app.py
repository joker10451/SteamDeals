import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from steam_api import SteamMarketAPI
from data_manager import DataManager

# Инициализация
steam_api = SteamMarketAPI()
data_manager = DataManager()

# Настройка страницы
st.set_page_config(
    page_title="Отслеживание цен Steam",
    page_icon="📈"
)

# Заголовок
st.title("📈 Отслеживание цен предметов Steam")

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
                        price = float(item.get('price', '0').replace(',', '.'))
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
    min_price = st.slider("Минимальная цена (₽)", 0, 10000, 0)
    max_price = st.slider("Максимальная цена (₽)", 0, 10000, 10000)

    for item_name in watched_items:
        item_data = data_manager.watched_items[item_name]
        current_price_data = steam_api.get_item_price(item_name)
        
        if current_price_data and 'lowest_price' in current_price_data:
            current_price = float(current_price_data['lowest_price'].replace('₽', '').replace(',', '.').strip())
            
            # Применяем фильтры
            if current_price < min_price or current_price > max_price:
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
            price_history = item_data['price_history']
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

# Обновление цен
if watched_items:
    if st.button("🔄 Обновить все цены"):
        with st.spinner("Обновление цен..."):
            for item_name in watched_items:
                price_data = steam_api.get_item_price(item_name)
                if price_data and 'lowest_price' in price_data:
                    current_price = float(price_data['lowest_price'].replace('₽', '').replace(',', '.').strip())
                    data_manager.update_price(item_name, current_price)
        st.success("Цены обновлены!")
        st.rerun()
