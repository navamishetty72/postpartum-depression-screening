import torch
import torch.nn as nn
import torch.optim as optim
try:
    from pipelines.synthetic_audio.models import PPDAudioCNN
    from pipelines.synthetic_audio.data_loader import get_dataloaders
except (ImportError, ModuleNotFoundError):
    from models import PPDAudioCNN
    from data_loader import get_dataloaders
import os

def train_model(epochs=20, lr=0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}")
    
    metadata_path = "../../data/synthetic/audio_metadata.csv"
    audio_dir = "../../data/synthetic/audio/"
    
    # Check if files exist to avoid runtime errors
    if not os.path.exists(metadata_path):
        print("Warning: Synthetic data not found. We will generate it in the next steps.")
        return

    train_loader, val_loader = get_dataloaders(metadata_path, audio_dir)
    
    model = PPDAudioCNN().to(device)
    criterion = nn.BCELoss() 
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        
        for batch_idx, (features, labels) in enumerate(train_loader):
            features, labels = features.to(device), labels.to(device).unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device).unsqueeze(1)
                outputs = model(features)
                val_loss += criterion(outputs, labels).item()
                
                predicted = (outputs > 0.5).float()
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
        print(f"Epoch [{epoch+1}/{epochs}] - Loss: {running_loss/len(train_loader):.4f} - Val Acc: {100 * correct / total:.2f}%")
        
    os.makedirs("../../data/processed/models", exist_ok=True)
    torch.save(model.state_dict(), "../../data/processed/models/audio_model.pth")
    print("Model saved successfully.")

if __name__ == "__main__":
    train_model()