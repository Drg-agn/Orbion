"""
Step 3 - train an LSTM autoencoder on CLEAN 6-hour windows and export it to ONNX.

The autoencoder squeezes each 36-step x 4-channel window (T, P, RH, Td, each
minus its window mean) through a small bottleneck and rebuilds it. It gets good
at rebuilding normal weather; faulty windows rebuild badly, so the
reconstruction error is the anomaly score.

The backend runs the exported .onnx with onnxruntime, so torch is only needed here.

  python ml/train_lstm_autoencoder.py --epochs 15
"""
import argparse, json
import numpy as np
import torch
from torch import nn

from common import MODELS, load_split, per_station
from app.ml.features import WINDOW, SEQ_CHANNELS, FEATURE_VERSION, frame_sequences


def windows(df, stride):
    out = []
    for _, g in per_station(df):
        if len(g) >= WINDOW:
            out.append(frame_sequences(g, np.arange(WINDOW - 1, len(g), stride)))
    return np.concatenate(out).astype(np.float32)


class LSTMAutoencoder(nn.Module):
    def __init__(self, n_ch=4, hidden=32, latent=16):
        super().__init__()
        self.encoder = nn.LSTM(n_ch, hidden, batch_first=True)
        self.to_latent = nn.Linear(hidden, latent)
        self.decoder = nn.LSTM(latent, hidden, batch_first=True)
        self.out = nn.Linear(hidden, n_ch)

    def forward(self, x):                      # x: (batch, 36, 4)
        _, (h, _) = self.encoder(x)
        z = self.to_latent(h[-1])              # (batch, latent)
        z = z.unsqueeze(1).repeat(1, x.shape[1], 1)
        y, _ = self.decoder(z)
        return self.out(y)


def errors(model, X, bs=2048):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), bs):
            xb = torch.from_numpy(X[i:i + bs])
            out.append(((model(xb) - xb) ** 2).mean(dim=(1, 2)).numpy())
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--stride", type=int, default=3, help="take every Nth window from train")
    ap.add_argument("--fpr", type=float, default=0.002)
    ap.add_argument("--batch", type=int, default=256)
    a = ap.parse_args()
    torch.manual_seed(0)

    Xtr = windows(load_split("train"), a.stride)
    scale = Xtr.reshape(-1, Xtr.shape[2]).std(axis=0) + 1e-6
    Xtr /= scale
    Xva = windows(load_split("val"), 1) / scale
    Xva = Xva.astype(np.float32)
    print(f"Train windows {len(Xtr):,} | val windows {len(Xva):,}")

    model = LSTMAutoencoder()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    best, best_state = np.inf, None
    for ep in range(1, a.epochs + 1):
        model.train()
        perm = np.random.permutation(len(Xtr))
        total = 0.0
        for i in range(0, len(perm), a.batch):
            xb = torch.from_numpy(Xtr[perm[i:i + a.batch]])
            loss = loss_fn(model(xb), xb)
            opt.zero_grad(); loss.backward(); opt.step()
            total += loss.item() * len(xb)
        val = float(errors(model, Xva[::5]).mean())
        print(f"epoch {ep:2d}  train {total / len(Xtr):.5f}  val {val:.5f}")
        if val < best:
            best, best_state = val, {k: v.clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    err = errors(model, Xva)
    meta = {
        "feature_version": FEATURE_VERSION,
        "channels": SEQ_CHANNELS,
        "window": WINDOW,
        "channel_scale": scale.tolist(),
        "center": float(np.median(err)),
        "threshold": float(np.quantile(err, 1 - a.fpr)),
        "target_fpr": a.fpr,
    }
    torch.save(model.state_dict(), MODELS / "lstm_autoencoder.pt")
    (MODELS / "lstm_autoencoder_meta.json").write_text(json.dumps(meta, indent=2))
    torch.onnx.export(model, torch.zeros(1, WINDOW, len(SEQ_CHANNELS)), MODELS / "lstm_autoencoder.onnx",
                      input_names=["window"], output_names=["reconstruction"],
                      dynamic_axes={"window": {0: "batch"}, "reconstruction": {0: "batch"}},
                      opset_version=17, dynamo=False)
    print(f"Saved -> {MODELS / 'lstm_autoencoder.onnx'}  (threshold {meta['threshold']:.5f})")


if __name__ == "__main__":
    main()
