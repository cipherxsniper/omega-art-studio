import numpy as np

def he_init(input_size, hidden_size):
    return np.random.randn(input_size, hidden_size) * np.sqrt(2/input_size)

class TwoLayerNet:
    def __init__(self, input_size, hidden_size, output_size):
        self.W1 = he_init(input_size, hidden_size)
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = he_init(hidden_size, output_size)
        self.b2 = np.zeros((1, output_size))

    def sigmoid(self, z):
        return 1 / (1 + np.exp(-z))

    def forward(self, X):
        self.z1 = X.dot(self.W1) + self.b1
        self.a1 = self.sigmoid(self.z1)
        self.z2 = self.a1.dot(self.W2) + self.b2
        self.a2 = self.sigmoid(self.z2)
        return self.a2

    def compute_loss(self, Y_hat, Y):
        loss = -np.mean(Y * np.log(Y_hat + 1e-8) + (1 - Y) * np.log(1 - Y_hat + 1e-8))
        return loss

    def backward(self, X, Y, Y_hat, lr=1.0):
        m = X.shape[0]
        dz2 = Y_hat - Y
        dW2 = self.a1.T.dot(dz2) / m
        db2 = np.sum(dz2, axis=0, keepdims=True) / m

        da1 = dz2.dot(self.W2.T)
        dz1 = da1 * self.a1 * (1 - self.a1)
        dW1 = X.T.dot(dz1) / m
        db1 = np.sum(dz1, axis=0, keepdims=True) / m

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2

    def train(self, X, Y, epochs=1000, lr=1.0):
        for i in range(epochs):
            Y_hat = self.forward(X)
            loss = self.compute_loss(Y_hat, Y)
            self.backward(X, Y, Y_hat, lr)
            if i % 100 == 0:
                print(f"Epoch {i}, loss: {loss:.4f}")

if __name__ == "__main__":
    X = np.array([[0,0],[0,1],[1,0],[1,1]])
    Y = np.array([[0],[1],[1],[0]])

    net = TwoLayerNet(input_size=2, hidden_size=8, output_size=1)
    net.train(X, Y, epochs=1000, lr=1.0)

    preds = net.forward(X) > 0.5
    print("Predictions:", preds.astype(int).ravel())
