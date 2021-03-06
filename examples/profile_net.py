#!/usr/bin/env python

"""
Profile network
===============

"""

import time
import deeppy as dp


def avg_running_time(fun, reps):
    # Memory allocation forces GPU synchronization
    start_time = time.time()
    for _ in range(reps):
        fun()
    return float(time.time() - start_time) / reps


def profile(net, feed, reps=50):
    feed = dp.Feed.from_any(feed)
    net.setup(*feed.shapes)
    net.phase = 'train'
    batch = next(feed.batches())
    x, y = batch
    total_duration = 0
    for layer_idx, layer in enumerate(net.layers[:-1]):
        def fprop():
            layer.fprop(x)
        fprop_duration = avg_running_time(fprop, reps)
        y = layer.fprop(x)
        layer.bprop_to_x = layer_idx > net.bprop_until

        def bprop():
            layer.bprop(y)
        bprop_duration = avg_running_time(bprop, reps)
        print('%s:   \tfprop(): %.6f s \t bprop(): %.6f s'
              % (layer.__class__.__name__, fprop_duration, bprop_duration))
        x = y
        total_duration += fprop_duration + bprop_duration
    print('total_duration: %.6f s' % total_duration)

    def nn_bprop():
        net.update(*batch)
    nn_bprop_duration = avg_running_time(nn_bprop, reps)
    print('net.bprop(): %.6f s' % nn_bprop_duration)


# Fetch CIFAR10 data
dataset = dp.dataset.CIFAR10()
x_train, y_train, x_test, y_test = dataset.arrays(dp_dtypes=True)

# Prepare network feeds
batch_size = 128
train_feed = dp.SupervisedFeed(x_train, y_train, batch_size=batch_size)

# Setup network
def conv_layer(n_filters):
    return dp.Convolution(
        n_filters=32,
        filter_shape=(5, 5),
        border_mode='full',
        weights=dp.Parameter(dp.AutoFiller(gain=1.25), weight_decay=0.003),
    )

def pool_layer():
    return dp.Pool(
        win_shape=(3, 3),
        strides=(2, 2),
        border_mode='same',
        method='max',
    )

net = dp.NeuralNetwork(
    layers=[
        conv_layer(32),
        dp.ReLU(),
        pool_layer(),
        conv_layer(32),
        dp.ReLU(),
        pool_layer(),
        conv_layer(64),
        dp.ReLU(),
        pool_layer(),
        dp.Flatten(),
        dp.Dropout(),
        dp.Affine(
            n_out=64,
            weights=dp.Parameter(dp.AutoFiller(gain=1.25), weight_decay=0.03)
        ),
        dp.ReLU(),
        dp.Affine(
            n_out=dataset.n_classes,
            weights=dp.Parameter(dp.AutoFiller(gain=1.25)),
        )
    ],
    loss=dp.SoftmaxCrossEntropy(),
)

profile(net, train_feed)
