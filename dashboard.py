import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Загрузка данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(BASE_DIR, 'Реестр-автотранспорта-2026.xlsx')
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Предобработка данных
df['Дата'] = pd.to_datetime(df['Дата'])
df['Время'] = pd.to_timedelta(df['Время'].astype(str))
df['Час_въезда'] = df['Время'].dt.total_seconds() / 3600
df['Час_въезда'] = df['Час_въезда'].astype(int)
df['Время_нахождения'] = df['Время нахождения на территории']

# Создание дополнительных колонок
df['Общий_груз'] = df['Кол-во паллет'] + df['Кол-во упаковок'] + df['Кол-во коробок']
df['Часовая_группа'] = pd.cut(df['Час_въезда'], 
                               bins=[0, 6, 12, 18, 24], 
                               labels=['Ночь (0-6)', 'Утро (6-12)', 'День (12-18)', 'Вечер (18-24)'])

# Расчёт метрик
total_operations = len(df)
avg_time = df['Время_нахождения'].mean()
median_time = df['Время_нахождения'].median()
loading_share = (df['Тип операции'] == 'Погрузка').mean() * 100
total_pallets = df['Кол-во паллет'].sum()
total_boxes = df['Кол-во коробок'].sum()
total_suppliers = df['Наименование поставщика'].nunique()

# Среднее количество операций в день
unique_days = df['Дата'].nunique()
avg_operations_per_day = total_operations / unique_days if unique_days > 0 else 0

# Тепловая карта (порядок дней)
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
df['День_недели_порядок'] = pd.Categorical(df['День недели'], categories=day_order, ordered=True)

# Инициализация Dash приложения
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server  # <-- ЭТА СТРОКА НУЖНА ДЛЯ РАБОТЫ НА RENDER
app.title = "Дашборд реестра автотранспорта"

# Определение цветовой схемы
colors = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'success': '#27ae60',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'info': '#1abc9c',
    'background': '#ecf0f1'
}

# Стили для карточек KPI (фиксированная ширина и высота)
kpi_card_style = {
    'backgroundColor': 'white',
    'borderRadius': '10px',
    'padding': '10px',
    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
    'textAlign': 'center',
    'margin': '5px',
    'height': '100%',
    'minHeight': '120px'
}

kpi_value_style = {
    'fontSize': '28px',
    'fontWeight': 'bold',
    'margin': '5px 0'
}

kpi_title_style = {
    'fontSize': '14px',
    'color': '#6c757d',
    'margin': '0'
}

# Layout дашборда
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("📊 Дашборд реестра автотранспорта", 
                        className="text-center mt-4 mb-4", 
                        style={'color': colors['primary']}), width=12)
    ]),
    
    # Фильтры
    dbc.Row([
        dbc.Col([
            html.Label("📅 Период:"),
            dcc.DatePickerRange(
                id='date-range',
                start_date=df['Дата'].min(),
                end_date=df['Дата'].max(),
                display_format='DD.MM.YYYY',
                style={'width': '100%'}
            )
        ], width=3),
        dbc.Col([
            html.Label("🏭 Тип операции:"),
            dcc.Dropdown(
                id='operation-type',
                options=[{'label': 'Все', 'value': 'Все'}] + 
                        [{'label': op, 'value': op} for op in df['Тип операции'].unique()],
                value='Все',
                clearable=False
            )
        ], width=3),
        dbc.Col([
            html.Label("📆 День недели:"),
            dcc.Dropdown(
                id='weekday',
                options=[{'label': 'Все', 'value': 'Все'}] + 
                        [{'label': day, 'value': day} for day in day_order],
                value='Все',
                clearable=False
            )
        ], width=3),
        dbc.Col([
            html.Label("🏢 Поставщик:"),
            dcc.Dropdown(
                id='supplier',
                options=[{'label': 'Все', 'value': 'Все'}] + 
                        [{'label': sup, 'value': sup} for sup in df['Наименование поставщика'].unique()[:20]],
                value='Все',
                clearable=True
            )
        ], width=3),
    ], className="mb-4"),
    
    # KPI карточки (8 карточек, одинаковый размер)
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("📦 Всего операций", style=kpi_title_style),
            html.H2(id="total-ops", style=kpi_value_style)
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("⏱ Среднее время", style=kpi_title_style),
            html.H2(id="avg-time", style=kpi_value_style),
            html.Small("мин", style={'color': '#6c757d'})
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("📊 Доля погрузки", style=kpi_title_style),
            html.H2(id="loading-share", style=kpi_value_style)
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("📦 Всего паллет", style=kpi_title_style),
            html.H2(id="total-pallets", style=kpi_value_style)
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("📦 Всего коробок", style=kpi_title_style),
            html.H2(id="total-boxes", style=kpi_value_style)
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("🏭 Всего поставщиков", style=kpi_title_style),
            html.H2(id="total-suppliers", style=kpi_value_style)
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("🎯 Медианное время", style=kpi_title_style),
            html.H2(id="median-time", style=kpi_value_style),
            html.Small("мин", style={'color': '#6c757d'})
        ]), style=kpi_card_style), width=3, lg=1.5),
        
        dbc.Col(dbc.Card(dbc.CardBody([
            html.P("📅 Операций в день", style=kpi_title_style),
            html.H2(id="avg-operations-per-day", style=kpi_value_style),
            html.Small("в среднем", style={'color': '#6c757d'})
        ]), style=kpi_card_style), width=3, lg=1.5),
    ], className="mb-4", justify="center"),
    
    # Графики - первый ряд
    dbc.Row([
        dbc.Col([dcc.Graph(id="daily-trend")], width=6),
        dbc.Col([dcc.Graph(id="hourly-analysis")], width=6),
    ], className="mb-4"),
    
    # Графики - второй ряд
    dbc.Row([
        dbc.Col([dcc.Graph(id="supplier-top")], width=6),
        dbc.Col([dcc.Graph(id="operation-comparison")], width=6),
    ], className="mb-4"),
    
    # Тепловые карты - третий ряд
    dbc.Row([
        dbc.Col([
            html.H4("🔥 Тепловая карта: медианное время (мин)", className="text-center mt-2 mb-2"),
            dcc.Graph(id="heatmap-time")
        ], width=6),
        dbc.Col([
            html.H4("📊 Тепловая карта: количество операций", className="text-center mt-2 mb-2"),
            dcc.Graph(id="heatmap-count")
        ], width=6),
    ], className="mb-4"),
    
    # Таблица выбросов
    dbc.Row([
        dbc.Col([
            html.H4("⚠️ Операции с аномальным временем (>120 минут)", className="mt-4 mb-3"),
            html.Div(id="outliers-table")
        ], width=12)
    ])
], fluid=True)

@app.callback(
    [Output("total-ops", "children"),
     Output("avg-time", "children"),
     Output("loading-share", "children"),
     Output("total-pallets", "children"),
     Output("total-boxes", "children"),
     Output("median-time", "children"),
     Output("total-suppliers", "children"),
     Output("avg-operations-per-day", "children"),
     Output("daily-trend", "figure"),
     Output("hourly-analysis", "figure"),
     Output("supplier-top", "figure"),
     Output("operation-comparison", "figure"),
     Output("heatmap-time", "figure"),
     Output("heatmap-count", "figure"),
     Output("outliers-table", "children")],
    [Input("date-range", "start_date"),
     Input("date-range", "end_date"),
     Input("operation-type", "value"),
     Input("weekday", "value"),
     Input("supplier", "value")]
)
def update_dashboard(start_date, end_date, operation_type, weekday, supplier):
    filtered_df = df.copy()
    
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df['Дата'] >= start_date) & 
                                  (filtered_df['Дата'] <= end_date)]
    if operation_type != 'Все':
        filtered_df = filtered_df[filtered_df['Тип операции'] == operation_type]
    if weekday != 'Все':
        filtered_df = filtered_df[filtered_df['День недели'] == weekday]
    if supplier != 'Все' and supplier:
        filtered_df = filtered_df[filtered_df['Наименование поставщика'] == supplier]
    
    # KPI
    total_ops_val = len(filtered_df)
    avg_time_val = filtered_df['Время_нахождения'].mean() if len(filtered_df) > 0 else 0
    loading_share_val = (filtered_df['Тип операции'] == 'Погрузка').mean() * 100 if len(filtered_df) > 0 else 0
    total_pallets_val = filtered_df['Кол-во паллет'].sum()
    total_boxes_val = filtered_df['Кол-во коробок'].sum()
    median_time_val = filtered_df['Время_нахождения'].median() if len(filtered_df) > 0 else 0
    total_suppliers_val = filtered_df['Наименование поставщика'].nunique()
    
    # Среднее количество операций в день
    unique_days_filt = filtered_df['Дата'].nunique()
    avg_ops_per_day = total_ops_val / unique_days_filt if unique_days_filt > 0 else 0
    
    # 1. Динамика операций по дням
    daily_ops = filtered_df.groupby('Дата').size().reset_index(name='Кол-во операций')
    daily_time = filtered_df.groupby('Дата')['Время_нахождения'].mean().reset_index()
    
    fig_daily = make_subplots(specs=[[{"secondary_y": True}]])
    fig_daily.add_trace(go.Bar(x=daily_ops['Дата'], y=daily_ops['Кол-во операций'], 
                                name="Кол-во операций", marker_color=colors['secondary']),
                        secondary_y=False)
    fig_daily.add_trace(go.Scatter(x=daily_time['Дата'], y=daily_time['Время_нахождения'],
                                   name="Среднее время (мин)", mode='lines+markers',
                                   marker_color=colors['danger'], line=dict(width=2)),
                        secondary_y=True)
    fig_daily.update_layout(title="Динамика операций и среднего времени по дням",
                            xaxis_title="Дата", hovermode='x unified', height=400)
    fig_daily.update_yaxes(title_text="Кол-во операций", secondary_y=False)
    fig_daily.update_yaxes(title_text="Среднее время (мин)", secondary_y=True)
    
    # 2. Часовой анализ
    hourly_stats_filt = filtered_df.groupby('Час_въезда').agg({
        'Время_нахождения': 'mean',
        'Тип операции': 'count'
    }).reset_index()
    
    fig_hourly = make_subplots(specs=[[{"secondary_y": True}]])
    fig_hourly.add_trace(go.Bar(x=hourly_stats_filt['Час_въезда'], 
                                y=hourly_stats_filt['Тип операции'],
                                name="Кол-во операций", marker_color=colors['info']),
                         secondary_y=False)
    fig_hourly.add_trace(go.Scatter(x=hourly_stats_filt['Час_въезда'],
                                    y=hourly_stats_filt['Время_нахождения'],
                                    name="Среднее время (мин)", mode='lines+markers',
                                    marker_color=colors['warning'], line=dict(width=2)),
                         secondary_y=True)
    fig_hourly.update_layout(title="Анализ по часам суток",
                             xaxis_title="Час въезда", hovermode='x unified', height=400)
    fig_hourly.update_yaxes(title_text="Кол-во операций", secondary_y=False)
    fig_hourly.update_yaxes(title_text="Среднее время (мин)", secondary_y=True)
    
    # 3. Топ поставщиков по количеству операций
    supplier_count = filtered_df.groupby('Наименование поставщика').size().sort_values(ascending=True).tail(10)
    
    fig_supplier = go.Figure(go.Bar(x=supplier_count.values, y=supplier_count.index,
                                    orientation='h', marker_color=colors['secondary'],
                                    text=supplier_count.values, textposition='outside'))
    fig_supplier.update_layout(title="Топ-10 поставщиков по количеству операций",
                               xaxis_title="Количество операций", yaxis_title="Поставщик",
                               height=400, margin=dict(l=0, r=0, t=40, b=0))
    
    # 4. Сравнение погрузка vs разгрузка
    op_comparison = filtered_df.groupby('Тип операции')['Время_нахождения'].agg(['mean', 'count']).reset_index()
    
    fig_op = make_subplots(specs=[[{"secondary_y": True}]])
    fig_op.add_trace(go.Bar(x=op_comparison['Тип операции'], y=op_comparison['count'],
                            name="Кол-во операций", marker_color=colors['success']),
                     secondary_y=False)
    fig_op.add_trace(go.Scatter(x=op_comparison['Тип операции'], y=op_comparison['mean'],
                                name="Среднее время (мин)", mode='lines+markers',
                                marker_color=colors['danger'], line=dict(width=2)),
                     secondary_y=True)
    fig_op.update_layout(title="Сравнение погрузки и разгрузки",
                         xaxis_title="Тип операции", height=400)
    fig_op.update_yaxes(title_text="Кол-во операций", secondary_y=False)
    fig_op.update_yaxes(title_text="Среднее время (мин)", secondary_y=True)
    
        # 5. Тепловая карта: медианное время
    heatmap_time_pivot = filtered_df.pivot_table(
        index='День_недели_порядок',
        columns='Час_въезда',
        values='Время_нахождения',
        aggfunc='median'
    ).fillna(0)
    
    fig_heatmap_time = go.Figure(data=go.Heatmap(
        z=heatmap_time_pivot.values,
        x=heatmap_time_pivot.columns.astype(int),
        y=heatmap_time_pivot.index,
        colorscale='RdYlGn_r',
        zmid=filtered_df['Время_нахождения'].median() if len(filtered_df) > 0 else 30,
        text=heatmap_time_pivot.values.round(0),
        texttemplate='%{text}',
        textfont={"size": 10, "color": "black"},
        hoverongaps=False
    ))
    fig_heatmap_time.update_layout(
        xaxis_title="Час въезда",
        yaxis_title="День недели",
        height=450,
        xaxis=dict(tickmode='linear', tick0=0, dtick=2)
    )
    fig_heatmap_time.update_coloraxes(colorbar_title_text="Медианное время (мин)")
    
    # 6. Тепловая карта: количество операций (ИСПРАВЛЕНО - среднее за день)
    # Создаём временную колонку с датой
    filtered_df_temp = filtered_df.copy()
    filtered_df_temp['Дата_день'] = filtered_df_temp['Дата'].dt.date
    
    # Считаем количество операций для каждой даты, дня недели и часа
    daily_counts = filtered_df_temp.groupby(['Дата_день', 'День_недели_порядок', 'Час_въезда']).size().reset_index(name='count')
    
    # Усредняем по всем датам для каждой комбинации день недели × час
    avg_counts = daily_counts.groupby(['День_недели_порядок', 'Час_въезда'])['count'].mean().reset_index()
    
    # Создаём сводную таблицу
    heatmap_count_pivot = avg_counts.pivot_table(
        index='День_недели_порядок',
        columns='Час_въезда',
        values='count'
    ).fillna(0)
    
    fig_heatmap_count = go.Figure(data=go.Heatmap(
        z=heatmap_count_pivot.values,
        x=heatmap_count_pivot.columns.astype(int),
        y=heatmap_count_pivot.index,
        colorscale='Blues',
        text=heatmap_count_pivot.values.round(1),
        texttemplate='%{text}',
        textfont={"size": 10, "color": "black"},
        hoverongaps=False,
        zmin=0
    ))
    fig_heatmap_count.update_layout(
        xaxis_title="Час въезда",
        yaxis_title="День недели",
        height=450,
        xaxis=dict(tickmode='linear', tick0=0, dtick=2)
    )
    fig_heatmap_count.update_coloraxes(colorbar_title_text="Среднее кол-во операций (в день)")
    
    # 7. Таблица выбросов
    outliers = filtered_df[filtered_df['Время_нахождения'] > 120].sort_values('Время_нахождения', ascending=False).head(20)
    
    if len(outliers) > 0:
        outliers_table = dbc.Table([
            html.Thead(html.Tr([html.Th("Дата"), html.Th("Поставщик"), html.Th("Тип операции"), 
                                html.Th("Время (мин)"), html.Th("Паллеты"), html.Th("Коробки")])),
            html.Tbody([
                html.Tr([
                    html.Td(row['Дата'].strftime('%d.%m.%Y')),
                    html.Td(row['Наименование поставщика']),
                    html.Td(row['Тип операции']),
                    html.Td(f"{row['Время_нахождения']:.0f}"),
                    html.Td(row['Кол-во паллет']),
                    html.Td(row['Кол-во коробок'])
                ]) for _, row in outliers.iterrows()
            ])
        ], bordered=True, hover=True, striped=True)
    else:
        outliers_table = html.P("Нет операций с временем более 120 минут", className="text-success")
    
    return (f"{total_ops_val:,}", f"{avg_time_val:.0f}", f"{loading_share_val:.0f}%", 
            f"{total_pallets_val:,.0f}", f"{total_boxes_val:,.0f}", f"{median_time_val:.0f}",
            f"{total_suppliers_val}", f"{avg_ops_per_day:.1f}",
            fig_daily, fig_hourly, fig_supplier, fig_op, 
            fig_heatmap_time, fig_heatmap_count, outliers_table)

if __name__ == '__main__':
    app.run(debug=True)