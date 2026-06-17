import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
# pyrefly: ignore [missing-import]
import joblib
import os

# Set seed for repeatability
np.random.seed(42)
n = 1000

# Path configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
dataset_path = os.path.join(current_dir, 'dataset.csv')
model_path = os.path.join(current_dir, 'model.pkl')

if not os.path.exists(dataset_path):
    # Generate original dataset
    data = {
        'nilai_matematika': np.random.randint(50, 100, n),
        'nilai_bahasa':     np.random.randint(50, 100, n),
        'nilai_ipa':        np.random.randint(50, 100, n),
        'nilai_ips':        np.random.randint(50, 100, n),
        'minat_teknologi':  np.random.randint(1, 6, n),
        'minat_seni':       np.random.randint(1, 6, n),
        'minat_bisnis':     np.random.randint(1, 6, n),
        'minat_kesehatan':  np.random.randint(1, 6, n),
    }

    jurusan = []
    for i in range(n):
        mat = data['nilai_matematika'][i]
        bhs = data['nilai_bahasa'][i]
        ipa = data['nilai_ipa'][i]
        ips = data['nilai_ips'][i]
        tek = data['minat_teknologi'][i]
        sen = data['minat_seni'][i]
        bis = data['minat_bisnis'][i]
        kes = data['minat_kesehatan'][i]

        if mat > 75 and tek >= 4:
            jurusan.append('Teknik Informatika')
        elif ipa > 75 and kes >= 4:
            jurusan.append('Kedokteran')
        elif mat > 70 and bis >= 4:
            jurusan.append('Manajemen')
        elif bhs > 75 and sen >= 4:
            jurusan.append('Sastra')
        elif ips > 75 and bis >= 3:
            jurusan.append('Akuntansi')
        elif ipa > 70:
            jurusan.append('Biologi')
        else:
            jurusan.append('Pendidikan')

    data['jurusan'] = jurusan
    df = pd.DataFrame(data)
    df.to_csv(dataset_path, index=False)
    print(f"Dataset berhasil dibuat di {dataset_path}")
else:
    df = pd.read_csv(dataset_path)
    print(f"Membaca dataset dari {dataset_path}")

X = df.drop('jurusan', axis=1)
y = df['jurusan']

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Fit Decision Tree model
dt = DecisionTreeClassifier(max_depth=7, random_state=42)
dt.fit(X_train, y_train)

# Calculate accuracy
acc_dt = accuracy_score(y_test, dt.predict(X_test))

print(f"Akurasi Decision Tree: {acc_dt:.2%}")
print(f"Akurasi: {acc_dt:.2%}")

# Save model & metadata in a dictionary
model_data = {
    'model': dt,
    'decision_tree': dt,
    'accuracies': {
        'decision_tree': float(acc_dt),
    },
    'dataset_size': len(df)
}

joblib.dump(model_data, model_path)
print(f"Model Decision Tree berhasil disimpan di {model_path}")