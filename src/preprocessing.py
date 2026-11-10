import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler

REQUIRED_COLUMNS = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']
FEATURE_COLUMNS = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount']


class DataPreprocessor:
    def __init__(self):
        self.required_columns = REQUIRED_COLUMNS
        self.feature_columns = FEATURE_COLUMNS

    def validate_columns(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Validate if all 31 required columns are present in DataFrame."""
        if df is None or not isinstance(df, pd.DataFrame):
            return False, "Input is not a valid DataFrame."

        missing = [col for col in self.required_columns if col not in df.columns]
        if missing:
            return False, f"Missing required columns ({len(missing)}): {', '.join(missing[:10])}{'...' if len(missing) > 10 else ''}"

        return True, ""

    def load_and_validate(self, filepath: str) -> tuple[pd.DataFrame, dict]:
        """Load CSV and validate columns. Returns (df, info_dict)."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found at: {filepath}")

        df = pd.read_csv(filepath)
        is_valid, error_msg = self.validate_columns(df)
        if not is_valid:
            raise ValueError(error_msg)

        total_rows = len(df)
        fraud_count = int((df['Class'] == 1).sum())
        legit_count = int((df['Class'] == 0).sum())
        fraud_rate = (fraud_count / total_rows * 100.0) if total_rows > 0 else 0.0
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

        info_dict = {
            'row_count': total_rows,
            'column_count': len(df.columns),
            'fraud_count': fraud_count,
            'legit_count': legit_count,
            'fraud_rate': round(float(fraud_rate), 4),
            'file_size_mb': round(float(file_size_mb), 2)
        }

        return df, info_dict

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop duplicate rows, remove or fill nulls, and enforce numeric data types."""
        cleaned_df = df.copy()

        # Drop duplicate records
        cleaned_df = cleaned_df.drop_duplicates()

        # Handle null values if any exist
        if cleaned_df.isnull().any().any():
            cleaned_df = cleaned_df.dropna()

        # Enforce numeric conversion
        for col in self.required_columns:
            if col in cleaned_df.columns:
                cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors='coerce')

        cleaned_df = cleaned_df.dropna()
        cleaned_df['Class'] = cleaned_df['Class'].astype(int)

        return cleaned_df

    def get_feature_columns(self) -> list:
        """Returns the 30 feature columns (Time, V1-V28, Amount)."""
        return list(self.feature_columns)

    def preprocess_for_training(self, df: pd.DataFrame, model_folder: str = None) -> tuple:
        """
        Splits data using StratifiedShuffleSplit (80/20).
        Scales 'Time' and 'Amount' features only.
        Saves scaler to models/scaler.pkl if model_folder is given.
        Returns (X_train, X_test, y_train, y_test, scaler).
        """
        X = df[self.feature_columns].copy()
        y = df['Class'].astype(int).values

        # Stratified split to maintain class balance in train and test sets
        sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(sss.split(X, y))

        X_train = X.iloc[train_idx].copy()
        X_test = X.iloc[test_idx].copy()
        y_train = y[train_idx]
        y_test = y[test_idx]

        # Fit StandardScaler on Time and Amount only (V1-V28 are already PCA scaled)
        scaler = StandardScaler()
        scale_cols = ['Time', 'Amount']
        X_train[scale_cols] = scaler.fit_transform(X_train[scale_cols])
        X_test[scale_cols] = scaler.transform(X_test[scale_cols])

        if model_folder:
            os.makedirs(model_folder, exist_ok=True)
            scaler_path = os.path.join(model_folder, 'scaler.pkl')
            joblib.dump(scaler, scaler_path)

        X_train_np = X_train.to_numpy(dtype=np.float64)
        X_test_np = X_test.to_numpy(dtype=np.float64)

        return X_train_np, X_test_np, y_train, y_test, scaler

    def preprocess_single(self, transaction_dict: dict, scaler) -> np.ndarray:
        """
        Preprocess a single transaction dictionary into a (1, 30) numpy array
        with Time and Amount properly scaled.
        """
        row = []
        for col in self.feature_columns:
            val = transaction_dict.get(col, 0.0)
            try:
                row.append(float(val))
            except (ValueError, TypeError):
                row.append(0.0)

        arr = np.array(row, dtype=np.float64).reshape(1, -1)
        if scaler is not None:
            # Scale Time (index 0) and Amount (index 29)
            arr[:, [0, 29]] = scaler.transform(arr[:, [0, 29]])

        return arr

    def get_analytics_data(self, df: pd.DataFrame) -> dict:
        """Compute all analytics data and return as a comprehensive dictionary."""
        total_transactions = int(len(df))
        if total_transactions == 0:
            return {
                'overview': {
                    'total_transactions': 0, 'fraud_count': 0, 'legit_count': 0,
                    'fraud_rate': 0.0, 'total_amount': 0.0, 'avg_amount': 0.0,
                    'max_amount': 0.0, 'min_amount': 0.0
                },
                'distribution': {},
                'time_series': {'bins': [], 'fraud_counts': [], 'legit_counts': [], 'total_counts': []},
                'amount_ranges': {'labels': [], 'fraud_counts': [], 'legit_counts': []},
                'correlation': {'features': [], 'matrix': []},
                'stats': {},
                'fraud_time_distribution': {'hours': [], 'counts': []},
                'amount_scatter': {'fraud': [], 'legit': []}
            }

        fraud_df = df[df['Class'] == 1]
        legit_df = df[df['Class'] == 0]

        fraud_count = int(len(fraud_df))
        legit_count = int(len(legit_df))
        fraud_rate = (fraud_count / total_transactions * 100.0) if total_transactions > 0 else 0.0

        total_amount = float(df['Amount'].sum())
        avg_amount = float(df['Amount'].mean())
        max_amount = float(df['Amount'].max())
        min_amount = float(df['Amount'].min())

        overview = {
            'total_transactions': total_transactions,
            'fraud_count': fraud_count,
            'legit_count': legit_count,
            'fraud_rate': round(float(fraud_rate), 4),
            'total_amount': round(total_amount, 2),
            'avg_amount': round(avg_amount, 2),
            'max_amount': round(max_amount, 2),
            'min_amount': round(min_amount, 2)
        }

        # 2. Distribution
        fraud_amount = float(fraud_df['Amount'].sum()) if fraud_count > 0 else 0.0
        legit_amount = float(legit_df['Amount'].sum()) if legit_count > 0 else 0.0
        fraud_avg = float(fraud_df['Amount'].mean()) if fraud_count > 0 else 0.0
        legit_avg = float(legit_df['Amount'].mean()) if legit_count > 0 else 0.0

        distribution = {
            'fraud_count': fraud_count,
            'legit_count': legit_count,
            'fraud_amount': round(fraud_amount, 2),
            'legit_amount': round(legit_amount, 2),
            'fraud_avg_amount': round(fraud_avg, 2),
            'legit_avg_amount': round(legit_avg, 2),
            'fraud_percentage': round(float(fraud_rate), 4),
            'legit_percentage': round(float(100.0 - fraud_rate), 4)
        }

        # 3. Time Series (48 hourly bins of 3600 seconds)
        max_time = float(df['Time'].max()) if total_transactions > 0 else 0.0
        num_bins = 48
        bin_series = (df['Time'] // 3600).astype(int).clip(0, num_bins - 1)

        time_bins = [f'{i}h' for i in range(num_bins)]
        fraud_time_counts = [0] * num_bins
        legit_time_counts = [0] * num_bins
        total_time_counts = [0] * num_bins

        # Group by bin and class
        time_class_counts = df.groupby([bin_series, 'Class']).size().unstack(fill_value=0)
        for i in range(num_bins):
            if i in time_class_counts.index:
                row = time_class_counts.loc[i]
                fc = int(row.get(1, 0))
                lc = int(row.get(0, 0))
                fraud_time_counts[i] = fc
                legit_time_counts[i] = lc
                total_time_counts[i] = fc + lc

        time_series = {
            'bins': time_bins,
            'fraud_counts': fraud_time_counts,
            'legit_counts': legit_time_counts,
            'total_counts': total_time_counts
        }

        # 4. Amount Ranges
        range_labels = ['$0-10', '$10-50', '$50-100', '$100-500', '$500-1000', '$1000+']
        range_bins = [-1.0, 10.0, 50.0, 100.0, 500.0, 1000.0, float('inf')]
        amount_cut = pd.cut(df['Amount'], bins=range_bins, labels=range_labels, right=True)
        amount_counts = df.groupby([amount_cut, 'Class'], observed=False).size().unstack(fill_value=0)

        range_fraud_counts = []
        range_legit_counts = []
        for label in range_labels:
            if label in amount_counts.index:
                row = amount_counts.loc[label]
                range_fraud_counts.append(int(row.get(1, 0)))
                range_legit_counts.append(int(row.get(0, 0)))
            else:
                range_fraud_counts.append(0)
                range_legit_counts.append(0)

        amount_ranges = {
            'labels': range_labels,
            'fraud_counts': range_fraud_counts,
            'legit_counts': range_legit_counts
        }

        # 5. Correlation Matrix (V1-V14 + Amount: 15 features)
        corr_cols = [f'V{i}' for i in range(1, 15)] + ['Amount']
        corr_df = df[corr_cols].corr().fillna(0.0).round(4)
        corr_matrix = [[round(float(v), 4) for v in row] for row in corr_df.values]

        correlation = {
            'features': corr_cols,
            'matrix': corr_matrix
        }

        # 6. Statistical Summary
        def _get_stats(series: pd.Series) -> dict:
            if len(series) == 0:
                return {'count': 0, 'mean': 0.0, 'std': 0.0, 'min': 0.0, 'p25': 0.0, 'median': 0.0, 'p75': 0.0, 'max': 0.0}
            desc = series.describe()
            return {
                'count': int(desc.get('count', 0)),
                'mean': round(float(desc.get('mean', 0.0)), 2),
                'std': round(float(desc.get('std', 0.0)), 2),
                'min': round(float(desc.get('min', 0.0)), 2),
                'p25': round(float(desc.get('25%', 0.0)), 2),
                'median': round(float(desc.get('50%', 0.0)), 2),
                'p75': round(float(desc.get('75%', 0.0)), 2),
                'max': round(float(desc.get('max', 0.0)), 2)
            }

        stats = {
            'fraud_amount': _get_stats(fraud_df['Amount']),
            'legit_amount': _get_stats(legit_df['Amount']),
            'overall_amount': _get_stats(df['Amount'])
        }

        # 7. Fraud Time Distribution (24-hour cycle: (Time // 3600) % 24)
        hourly_fraud = [0] * 24
        if fraud_count > 0:
            fraud_hours = ((fraud_df['Time'] // 3600) % 24).astype(int)
            hour_counts = fraud_hours.value_counts()
            for h in range(24):
                hourly_fraud[h] = int(hour_counts.get(h, 0))

        fraud_time_distribution = {
            'hours': [f'{h:02d}:00' for h in range(24)],
            'counts': hourly_fraud
        }

        # 8. Amount Scatter (sample 500 fraud + 500 legit points: Amount, V1)
        fraud_sample = fraud_df[['Amount', 'V1']].head(500)
        legit_sample_size = min(500, legit_count)
        legit_sample = legit_df[['Amount', 'V1']].sample(n=legit_sample_size, random_state=42) if legit_sample_size > 0 else legit_df[['Amount', 'V1']]

        amount_scatter = {
            'fraud': [
                {'amount': round(float(r['Amount']), 2), 'v1': round(float(r['V1']), 4)}
                for _, r in fraud_sample.iterrows()
            ],
            'legit': [
                {'amount': round(float(r['Amount']), 2), 'v1': round(float(r['V1']), 4)}
                for _, r in legit_sample.iterrows()
            ]
        }

        return {
            'overview': overview,
            'distribution': distribution,
            'time_series': time_series,
            'amount_ranges': amount_ranges,
            'correlation': correlation,
            'stats': stats,
            'fraud_time_distribution': fraud_time_distribution,
            'amount_scatter': amount_scatter
        }
