import numpy as np
import pickle
import sys

import keras.backend as K
from keras.layers import Input, Dense
from keras.models import Model
from keras.optimizers import SGD, Adam

# Command line arguments
lam = float(sys.argv[1])
seed = int(sys.argv[2])
np.random.seed = seed

# Prepare data
fd = open("jets-pile.pickle", "rb")
X_train, X_test, y_train, y_test, z_train, z_test = pickle.load(fd)
X = X_train
y = y_train
z = z_train
fd.close()

# mask = (z_train[:, 0] == 1)
# X_train = X_train[mask]
# y_train = y_train[mask]
# z_train = z_train[mask]

# Set network architectures
inputs = Input(shape=(X.shape[1],))
Dx = Dense(64, activation="tanh")(inputs)
Dx = Dense(64, activation="relu")(Dx)
Dx = Dense(64, activation="relu")(Dx)
Dx = Dense(1, activation="sigmoid")(Dx)
D = Model(inputs=[inputs], outputs=[Dx])

Rx = D(inputs)
Rx = Dense(64, activation="relu")(Rx)
Rx = Dense(64, activation="relu")(Rx)
Rx = Dense(64, activation="relu")(Rx)
Rx = Dense(z.shape[1], activation="softmax")(Rx)
R = Model(inputs=[inputs], outputs=[Rx])


def make_loss_D(c):
    def loss_D(y_true, y_pred):
        return c * K.binary_crossentropy(y_true, y_pred)
    return loss_D


def make_loss_R(c):
    def loss_R(z_true, z_pred):
        return c * K.categorical_crossentropy(z_true, z_pred)
    return loss_R


opt_D = Adam()
D.compile(loss=[make_loss_D(c=1.0)], optimizer=opt_D)

opt_DRf = SGD(momentum=0)
DRf = Model(inputs=[inputs], outputs=[D(inputs), R(inputs)])
DRf.compile(loss=[make_loss_D(c=1.0),
                  make_loss_R(c=-lam)],
            optimizer=opt_DRf)

opt_DfR = SGD(momentum=0)
DfR = Model(inputs=[inputs], outputs=[R(inputs)])
DfR.compile(loss=[make_loss_R(c=1.0)],
            optimizer=opt_DfR)

# Pretraining of D
D.trainable = True
R.trainable = False
D.fit(X_train, y_train, epochs=20)

# Pretraining of R
if lam > 0.0:
    D.trainable = False
    R.trainable = True
    DfR.fit(X_train[y_train == 0], z_train[y_train == 0], epochs=20)
    # DfR.fit(X_train, z_train, epochs=20)

# Adversarial training
batch_size = 128

for i in range(1001):
    print(i)

    # Fit D
    D.trainable = True
    R.trainable = False
    indices = np.random.permutation(len(X_train))[:batch_size]
    DRf.train_on_batch(X_train[indices], [y_train[indices], z_train[indices]])

    # Fit R
    if lam > 0.0:
        D.trainable = False
        R.trainable = True

        DfR.fit(X_train[y_train == 0], z_train[y_train == 0],
                batch_size=batch_size, epochs=1, verbose=0)
        # DfR.fit(X_train, z_train,
        #         batch_size=batch_size, epochs=1, verbose=0)

D.save_weights("D-%.4f-%d-z=0.h5" % (lam, seed))
