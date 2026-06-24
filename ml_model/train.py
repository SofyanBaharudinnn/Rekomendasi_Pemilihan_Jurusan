import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os
import csv

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
    
    with open(dataset_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        header = ['nilai_matematika', 'nilai_bahasa', 'nilai_ipa', 'nilai_ips',
                  'minat_teknologi', 'minat_seni', 'minat_bisnis', 'minat_kesehatan', 'jurusan']
        writer.writerow(header)
        for i in range(n):
            writer.writerow([
                data['nilai_matematika'][i],
                data['nilai_bahasa'][i],
                data['nilai_ipa'][i],
                data['nilai_ips'][i],
                data['minat_teknologi'][i],
                data['minat_seni'][i],
                data['minat_bisnis'][i],
                data['minat_kesehatan'][i],
                data['jurusan'][i]
            ])
    print(f"Dataset berhasil dibuat di {dataset_path}")
else:
    # Bersihkan dan samakan pemisah (semicolon) jika ada baris yang rusak
    cleaned_rows = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ';' in line:
                parts = [p.strip() for p in line.split(';')]
            else:
                parts = [p.strip() for p in line.split(',')]
            while parts and parts[-1] == '':
                parts.pop()
            if len(parts) >= 9:
                cleaned_rows.append(parts[:9])
                
    with open(dataset_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerows(cleaned_rows)

# Membaca dataset dari berkas yang sudah bersih tanpa pandas
features_list = []
labels_list = []

with open(dataset_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    header = [h.strip() for h in next(reader)]
    
    jurusan_idx = header.index('jurusan')
    feature_indices = [i for i, h in enumerate(header) if h != 'jurusan' and h != '']
    
    for row in reader:
        if not row or len(row) <= max(feature_indices + [jurusan_idx]):
            continue
        try:
            feat = [float(row[idx]) for idx in feature_indices]
            label = row[jurusan_idx].strip()
            features_list.append(feat)
            labels_list.append(label)
        except ValueError:
            continue

X = np.array(features_list)
y = np.array(labels_list)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

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
    'dataset_size': len(X)
}

joblib.dump(model_data, model_path)
print(f"Model Decision Tree berhasil disimpan di {model_path}")