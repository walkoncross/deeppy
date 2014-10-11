import cudarray as ca
from ..base import parameter


class Layer(object):
    def _setup(self, input_shape):
        """ Setup layer with parameters that are unknown at __init__(). """
        pass

    def fprop(self, X, phase):
        """ Calculate layer output for given input (forward propagation). """
        raise NotImplementedError()

    def bprop(self, Y_grad):
        """ Calculate input gradient. """
        raise NotImplementedError()

    def output_shape(self, input_shape):
        """ Calculate shape of this layer's output.
        input_shape[0] is the number of samples in the input.
        input_shape[1:] is the shape of the feature.
        """
        raise NotImplementedError()


class LossMixin(object):
    def loss(self, Y_true, Y_pred):
        """ Calculate mean loss given output and predicted output. """
        raise NotImplementedError()

    def input_grad(self, Y_true, Y_pred):
        """ Calculate input gradient given output and predicted output. """
        raise NotImplementedError()


class ParamMixin(object):
    def params(self):
        """ Layer parameters. """
        raise NotImplementedError()


class FullyConnected(Layer, ParamMixin):
    def __init__(self, n_output, weights, bias=0.0, weight_decay=0.0):
        self.name = 'fullconn'
        self.n_output = n_output
        self.W = parameter(weights)
        self.b = parameter(bias)

    def _setup(self, input_shape):
        n_input = input_shape[1]
        W_shape = (n_input, self.n_output)
        b_shape = self.n_output
        self.W._setup(W_shape)
        if not self.W.name:
            self.W.name = self.name + '_W'
        self.b._setup(b_shape)
        if not self.b.name:
            self.b.name = self.name + '_b'

    def fprop(self, X, phase):
        self.last_X = X
        return ca.dot(X, self.W.values) + self.b.values

    def bprop(self, Y_grad):
        ca.dot(self.last_X.T, Y_grad, out=self.W.grad)
        ca.sum(Y_grad, axis=0, out=self.b.grad)
        return ca.dot(Y_grad, self.W.values.T)

    def params(self):
        return self.W, self.b

    def output_shape(self, input_shape):
        return (input_shape[0], self.n_output)


class Activation(Layer):
    def __init__(self, type):
        self.name = 'act_'
        if type == 'sigmoid':
            self.name = self.name+'sigm'
            self.fun = ca.nnet.sigmoid
            self.fun_d = ca.nnet.sigmoid_d
        elif type == 'relu':
            self.name = self.name+type
            self.fun = ca.nnet.relu
            self.fun_d = ca.nnet.relu_d
        elif type == 'tanh':
            self.name = self.name+type
            self.fun = ca.tanh
            self.fun_d = ca.nnet.tanh_d
        else:
            raise ValueError('Invalid activation function.')

    def fprop(self, X, phase):
        self.last_X = X
        return self.fun(X)

    def bprop(self, Y_grad):
        self.fun_d(self.last_X, self.last_X)
        self.last_X *= Y_grad
        return self.last_X

    def output_shape(self, input_shape):
        return input_shape


class MultinomialLogReg(Layer, LossMixin):
    """ Multinomial logistic regression with a cross-entropy loss function. """
    def __init__(self):
        self.name = 'logreg'

    def fprop(self, X, phase):
        return ca.nnet.softmax(X)

    def bprop(self, Y_grad):
        raise NotImplementedError(
            'MultinomialLogReg does not support back-propagation of gradients.'
            + ' It should occur only as the last layer of a NeuralNetwork.'
        )

    def input_grad(self, y, y_pred):
        # Assumes one-hot encoding.
        return -(y - y_pred)

    def loss(self, y, y_pred):
        # Assumes one-hot encoding.
        return ca.nnet.categorical_cross_entropy(y, y_pred)

    def output_shape(self, input_shape):
        return input_shape
