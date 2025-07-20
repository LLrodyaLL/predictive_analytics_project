import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# Примерные данные
data = pd.DataFrame({
    "Рейтинг": [4.9, 4.2, 3.8, 4.7, 4.1],
    "Заказы": [200, 30, 100, 50, 20],
    "Количество отзывов на конец периода": [24, 48, 72, 36, 60],
    "Продвигать": [1, 0, 0, 1, 0]
})

X = data[["Рейтинг", "Заказы", "Количество отзывов на конец периода"]]
y = data["Продвигать"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "model.pkl")
print("Модель сохранена как model.pkl")
