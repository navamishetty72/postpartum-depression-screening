import soundfile as sf
import os
import torch
import torchaudio
import pandas as pd
from torch.utils.data import Dataset, DataLoader

class PPDAudioDataset(Dataset):
    def __init__(self, metadata_csv, audio_dir, target_sample_rate=16000, n_mfcc=40, max_length=160000):
        self.metadata = pd.read_csv(metadata_csv)
        self.audio_dir = audio_dir
        self.target_sample_rate = target_sample_rate
        self.max_length = max_length
        self.mfcc_transform = torchaudio.transforms.MFCC(
            sample_rate=self.target_sample_rate,
            n_mfcc=n_mfcc
        )

    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, idx):
        file_name = self.metadata.iloc[idx]['filename']
        audio_path = os.path.join(self.audio_dir, file_name)
        
        # Load audio using soundfile instead of torchaudio
        audio_np, sample_rate = sf.read(audio_path)
        waveform = torch.tensor(audio_np, dtype=torch.float32)
        
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
        elif waveform.ndim == 2 and waveform.shape[0] > waveform.shape[1]:
            waveform = waveform.t()
            
        if sample_rate != self.target_sample_rate:
            resampler = torchaudio.transforms.Resample(sample_rate, self.target_sample_rate)
            waveform = resampler(waveform)
            
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
            
        if waveform.shape[1] > self.max_length:
            waveform = waveform[:, :self.max_length]
        else:
            padding = self.max_length - waveform.shape[1]
            waveform = torch.nn.functional.pad(waveform, (0, padding))
            
        mfcc_features = self.mfcc_transform(waveform)
        label = torch.tensor(self.metadata.iloc[idx]['label'], dtype=torch.float32)
        
        return mfcc_features, label

def get_dataloaders(metadata_csv, audio_dir, batch_size=32, split_ratio=0.8):
    dataset = PPDAudioDataset(metadata_csv, audio_dir)
    train_size = int(split_ratio * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, val_loader