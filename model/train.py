import numpy as np
import pandas as pd
import tensorflow_datasets as tfds
import re
import os
import datetime
import tensorflow as tf
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Input, Embedding, LSTM, Dense, Concatenate, Flatten, Dropout, GaussianNoise
from tensorflow.keras.callbacks import ModelCheckpoint, TensorBoard

from pandas.io.json import json_normalize  

training_set = pd.read_json('../dump/features-training.json', lines=True)
validation_set = pd.read_json('../dump/features-validation.json', lines=True)

def get_feature(dataset, name):
  for item in dataset['features']:
    yield item[name]

def normalize_text(item):
  text = re.sub('\s+', ' ', item).strip().lower()
  return re.sub('\d', '0', text)

def get_col(dataset, name):
  return [normalize_text(item) if item else '' for item in get_feature(dataset, name)]

def flat(list):
  return [item for sublist in list for item in sublist]

def get_cols(dataset, names): 
   return list(set(flat(get_col(dataset, name) for name in names)))
  
def get_style(dataset, name):
  for item in dataset['features']:
    style = item['computedStyle']
    if style and name in style:
      yield style[name]
    else:
      yield ''

used_styles = [
    'cursor',
    'border',
    'position',
    'display',
    'visibility',
    'opacity',
    'border-radius',
    'color'
]

all_style_values = list(set(flat([get_style(training_set, style) for style in used_styles])))
style_encoder = tfds.features.text.SubwordTextEncoder.build_from_corpus(all_style_values,  target_vocab_size=2**10)

text_encoder = tfds.features.text.SubwordTextEncoder.build_from_corpus(get_col(training_set, 'text') + get_col(training_set, 'title') + get_col(training_set, 'alt'), target_vocab_size=2**11)

# tagname encoder can get more than one tag with tagNamesWithin
tagname_encoder = tfds.features.text.TokenTextEncoder(get_cols(training_set, ['tagName', 'parentTagName', 'tagNamesWithin']))
attributes_encoder = tfds.features.text.TokenTextEncoder(get_cols(training_set, ['attributes']))
classlist_encoder = tfds.features.text.SubwordTextEncoder.build_from_corpus(get_cols(training_set, ['classList', 'descendentsClassList']), target_vocab_size=2**11)
name_id_encoder = tfds.features.text.SubwordTextEncoder.build_from_corpus(get_cols(training_set, ['id', 'name']),  target_vocab_size=2**11)

def one_hot_encode_and_pad(data, encoder, max_number_of_tokens = 40):
  vec = np.zeros((len(data), max_number_of_tokens, encoder.vocab_size))
  for i, datum in enumerate(data):
    for j, item in enumerate(encoder.encode(datum)):
      vec[i, j, item] = 1
  return vec

def encode_and_pad(data, encoder, max_number_of_tokens = 40):
  return pad_sequences([encoder.encode(item) for item in data], padding='post', maxlen=max_number_of_tokens)

def get_input_vectors(dataset):
  return [
      encode_and_pad(get_col(dataset, 'tagName'), tagname_encoder, 1),
      encode_and_pad(get_col(dataset, 'parentTagName'), tagname_encoder, 1),
      encode_and_pad(get_col(dataset, 'text'), text_encoder, 40),
      encode_and_pad(get_col(dataset, 'title'), text_encoder, 40),
      encode_and_pad(get_col(dataset, 'alt'), text_encoder, 40),
      encode_and_pad(get_col(dataset, 'attributes'), attributes_encoder, 10),
      encode_and_pad(get_col(dataset, 'name'), name_id_encoder, 5),
      encode_and_pad(get_col(dataset, 'id'), name_id_encoder, 5),
      encode_and_pad(get_col(dataset, 'classList'), classlist_encoder, 20),
      encode_and_pad(get_col(dataset, 'descendentsClassList'), classlist_encoder, 20),
      encode_and_pad(get_col(dataset, 'tagNamesWithin'), tagname_encoder, 10),
  ] + [encode_and_pad(get_style(dataset, style), style_encoder, 5) for style in used_styles]

def get_labels(dataset):
  return dataset['label']

def get_text_embedding(name, encoder, input_sequence_size = 40):
  #text_input = Input(shape=(input_sequence_size,encoder.vocab_size))
  #return text_input, text_input
  text_input = Input(name='Input-' + name, shape=(input_sequence_size, ))
  text_input_embedding = Embedding(encoder.vocab_size, output_dim=512, name='Encoder-' + name)(text_input)
  return text_input, text_input_embedding

tagname, tagname_embedding = get_text_embedding('tagName', tagname_encoder, 1)
parent_tagname, parent_tagname_embedding = get_text_embedding('parent-tagName', tagname_encoder, 1)
element_text, element_text_embedding = get_text_embedding('textContent', text_encoder)
element_title, element_title_embedding = get_text_embedding('title', text_encoder)
element_alt, element_alt_embedding = get_text_embedding('alt', text_encoder)
attributes, attributes_embedding = get_text_embedding('attributes', attributes_encoder, 10)
element_name, element_name_embedding = get_text_embedding('name', name_id_encoder, 5)
element_id, element_id_embedding = get_text_embedding('id', name_id_encoder, 5)
class_list, class_list_embedding = get_text_embedding('className', classlist_encoder, 20)
descendent_class_list, descendent_class_list_embedding = get_text_embedding('descendent-className', classlist_encoder, 20)
tagnames_within, tagnames_within_encoding = get_text_embedding('tagNames-within', tagname_encoder, 10)

style_embeddings = [get_text_embedding('style-' + style, style_encoder, 5) for style in used_styles]

style_networks = Concatenate(name='All-CSS-Styles')([ Flatten()(style_encoding) for style_input, style_encoding in style_embeddings])
style_network = Dense(256, name='Style-Perceptron')(style_networks)

classes_and_styles_biases = Concatenate(name='IdAndClassBias')([
    Flatten()(element_id_embedding),
    Flatten()(class_list_embedding),
    Flatten()(descendent_class_list_embedding)
])
classes_and_styles_bias = Dense(256, name='IdClass-Perceptron')(classes_and_styles_biases)

text_inputs_after_concat = Concatenate()([
    Flatten()(tagname_embedding),
    Flatten()(parent_tagname_embedding),
    Flatten()(element_text_embedding),
    Flatten()(element_title_embedding),
    Flatten()(element_alt_embedding),
    Flatten()(attributes_embedding),
    Flatten()(element_name_embedding),
    Flatten()(element_id_embedding),
    Flatten()(class_list_embedding),
    Flatten()(descendent_class_list_embedding),
    Flatten()(tagnames_within_encoding),
    style_network,
    classes_and_styles_bias
])
text_after_dense = Dense(512)(text_inputs_after_concat)
noise = GaussianNoise(0.1)(text_after_dense)
dense2 = Dense(256)(noise)
dropout = Dropout(rate=0.05)(dense2)
dense3 = Dense(256, activation='relu')(dropout)

out_layer = Dense(1)(dense3)

model = Model([
    tagname,
    parent_tagname,
    element_text,
    element_title,
    element_alt,
    attributes,
    element_name,
    element_id,
    class_list,
    descendent_class_list,
    tagnames_within
] + [style_input for style_input, style_encoding in style_embeddings], [out_layer])

model.compile(optimizer='adam', loss='mean_squared_error', metrics=['accuracy'])

logdir = os.path.join("logs", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
tensorboard_callback = tf.keras.callbacks.TensorBoard(logdir, histogram_freq=1)

model.fit(x=get_input_vectors(training_set), y=get_labels(training_set), 
          validation_data=(get_input_vectors(validation_set), get_labels(validation_set)),
          callbacks=[tensorboard_callback], batch_size=64, epochs=20)

model.save("model.h5")
