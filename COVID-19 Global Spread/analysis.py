import requests
import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
import numpy as np

# Veri
confirmed_csv = 'corona_confirmed.csv'
confirmed_github = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'

# Veriyi indirme
response = requests.get(confirmed_github)  # URL'den veri çek
with open(confirmed_csv, 'wb') as file:  # CSV dosyasını ikili modda aç
    file.write(response.content)  # İndirilen veriyi dosyaya kaydet

# Veriyi yükleme
data = pd.read_csv(confirmed_csv)
# -----------------------------------------------------

# Veriyi işleme
data = data.melt(id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'],
                 var_name='Date',
                 value_name='Confirmed')

# Tarih formatını belirlenmesi
data['Date'] = pd.to_datetime(data['Date'],
                              format='%m/%d/%y')

# Veriyi grup ve toplama
data = data.groupby(['Date', 'Country/Region', 'Lat', 'Long']).sum().reset_index()

# Ülkeler için toplam vaka sayılarını hesaplama ve yeniden adlandırma
country_totals = data.groupby('Country/Region')['Confirmed'].sum().reset_index()

country_totals = country_totals.rename(columns={'Confirmed': 'Total_Confirmed'})

# Ülkeleri toplam vaka sayılarına göre sıralama
country_totals = country_totals.sort_values(by='Total_Confirmed', ascending=False).reset_index(drop=True)
# ------------------------------------------------------

# Yüzdelik dilimlere göre sınıflandırma
n = len(country_totals)
third = n // 3

country_totals['Color'] = 'green'

# En yüksek %33
country_totals.iloc[:third, country_totals.columns.get_loc('Color')] = 'red'

# Orta %33
country_totals.iloc[third:2 * third, country_totals.columns.get_loc('Color')] = 'darkblue'

# Ülke adlarını ve renklerini içeren sözlük
country_colors = dict(zip(country_totals['Country/Region'], country_totals['Color']))


# --------------------------------------------------------------

# Yarı çap için normalize etme işlevi
def get_radius(value, min_value, max_value, min_radius=1, max_radius=22):
    if max_value > min_value:
        # Logaritmik dönüşüm uygulayın
        log_min_value = np.log1p(min_value)
        log_max_value = np.log1p(max_value)
        log_value = np.log1p(value)

        radius = min_radius + (max_radius - min_radius) * (log_value - log_min_value) / (log_max_value - log_min_value)
        # Logaritmik dönüştürülmüş değeri, min_radius ve max_radius arasında normalize eder
        return radius
    else:
        return min_radius


# Min ve max değerleri belirleyin
min_confirmed = data['Confirmed'].min()
max_confirmed = data['Confirmed'].max()


# -------------------------------------------------------------


def create_geojson(dataa):
    features = []

    # DataFrame'i 'Date' sütununa göre gruplandırarak her tarih için verileri işleme
    for date, group in dataa.groupby('Date'):

        for _, row in group.iterrows():  # Her grubun satırlarını döngüyle sırayla işleme
            if row['Confirmed'] > 0:
                # Onaylanan vaka sayısına göre bir radius hesaplama
                radius = get_radius(row['Confirmed'], min_confirmed, max_confirmed)
                # Ülkeye özel bir renk belirleme
                country_color = country_colors.get(row['Country/Region'], 'gray')  # Varsayılan renk 'gri'

                # GeoJSON formatında bir özellikler
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",  # Nokta türünde coğrafi bilgi
                        "coordinates": [row['Long'], row['Lat']]  # Noktanın enlem ve boylam bilgisi
                    },
                    "properties": {  # GeoJSON'un ilgili noktasının özellikleri
                        "time": date.strftime('%Y-%m-%d'),  # Zaman bilgisi (tarih formatında)
                        "style": {  # Harita üzerinde gösterim stili
                            "color": country_color,  # Ülkeye atanmış renk
                            "weight": 2  # Sınır kalınlığı
                        },
                        "icon": "circle",  # Noktanın haritada nasıl görüneceği (daire olarak)
                        "iconstyle": {
                            "radius": radius,  # Vaka sayısına göre hesaplanan dairenin yarıçapı
                            "fillColor": country_color,  # Dairenin dolgu rengi (ülkenin rengi)
                            "fillOpacity": 1  # Dairenin opaklığı
                        },
                        # Popup metni, harita üzerinde noktanın tıklanabilir bilgisi
                        "popup": f"Confirmed cases: {row['Confirmed']}"
                    }
                }

                features.append(feature)

    # Tüm özellikler bir arada toplama
    return {
        "type": "FeatureCollection",  # GeoJSON formatında bir özellik koleksiyonu
        "features": features  # İşlenmiş olan tüm özelliklerin listesi
    }


# Verileri kullanarak GeoJSON verisi oluştur
geojson_data = create_geojson(data)

# Haritayı oluştur, başlangıç konumu 20 derece enlem ve 0 derece boylam, başlangıç zoom seviyesi 2
m = folium.Map(location=[20, 0], zoom_start=2)

# Zaman temelli harita katmanı ekle
TimestampedGeoJson(
    geojson_data,
    period='P1D',  # Her bir veri noktası için zaman periyodu 1 gün olarak ayarlanıyor
    duration='P1D',  # Her bir veri noktası haritada 1 gün boyunca görünecek
    max_speed=200,  # Otomatik oynatma hızını 200 ile sınırlıyoruz
    loop=True,  # Harita animasyonu döngü

).add_to(m)  # Harita üzerine bu zaman temelli katmanı ekle

# Haritayı bir HTML dosyası olarak kaydet
m.save('animated_map.html')
