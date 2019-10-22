# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import binascii
import base64#file encode
# import urllib2 #file download from url
import argparse
import os.path
import re
import sys
import tarfile

import numpy as np
from six.moves import urllib
import tensorflow as tf


from odoo import models, fields, api




class Importimage (models.Model):
    _name = 'image_recognizer.images'
    animalname = fields.Char(string="Photo recognition")
    name = fields.Char(string="Record Description")
    probability = fields.Float(string="Prediction accuracy", store=True)
    imager = fields.Binary()
    datas = fields.Char()
    # description = fields.Char()
    image_filename = fields.Char("DONDOLO")



    def predict_image(self):
        datas = self.imager

        if datas:
            script_dir = os.path.dirname(
                __file__)  # <-- absolute dir the script is in
            rel_path = "files/imagetorecognize.jpg"
            abs_file_path = os.path.join(script_dir, rel_path)
            imagesa = open(abs_file_path, 'wb+')
            imagesa.write(base64.b64decode(datas))
            imagesa.close()

        class NodeLookup(object):

            def __init__(self,
                         label_lookup_path=None,
                         uid_lookup_path=None):
                if not label_lookup_path:
                    label_lookup_path = os.path.join(
                        FLAGS.model_dir,
                        'imagenet_2012_challenge_label_map_proto.pbtxt')
                if not uid_lookup_path:
                    uid_lookup_path = os.path.join(
                        FLAGS.model_dir,
                        'imagenet_synset_to_human_label_map.txt')
                self.node_lookup = self.load(label_lookup_path,
                                             uid_lookup_path)

            def load(self, label_lookup_path, uid_lookup_path):
                """Loads a human readable English name for each softmax node.

                Args:
                  label_lookup_path: string UID to integer node ID.
                  uid_lookup_path: string UID to human-readable string.

                Returns:
                  dict from integer node ID to human-readable string.
                """
                if not tf.gfile.Exists(uid_lookup_path):
                    tf.logging.fatal('File does not exist %s', uid_lookup_path)
                if not tf.gfile.Exists(label_lookup_path):
                    tf.logging.fatal('File does not exist %s',
                                     label_lookup_path)

                # Loads mapping from string UID to human-readable string
                proto_as_ascii_lines = tf.gfile.GFile(
                    uid_lookup_path).readlines()
                uid_to_human = {}
                p = re.compile(r'[n\d]*[ \S,]*')
                for line in proto_as_ascii_lines:
                    parsed_items = p.findall(line)
                    uid = parsed_items[0]
                    human_string = parsed_items[2]
                    uid_to_human[uid] = human_string

                # Loads mapping from string UID to integer node ID.
                node_id_to_uid = {}
                proto_as_ascii = tf.gfile.GFile(label_lookup_path).readlines()
                for line in proto_as_ascii:
                    if line.startswith('  target_class:'):
                        target_class = int(line.split(': ')[1])
                    if line.startswith('  target_class_string:'):
                        target_class_string = line.split(': ')[1]
                        node_id_to_uid[target_class] = target_class_string[
                                                       1:-2]

                # Loads the final mapping of integer node ID to human-readable string
                node_id_to_name = {}
                for key, val in node_id_to_uid.items():
                    if val not in uid_to_human:
                        tf.logging.fatal('Failed to locate: %s', val)
                    name = uid_to_human[val]
                    node_id_to_name[key] = name

                return node_id_to_name

            def id_to_string(self, node_id):
                if node_id not in self.node_lookup:
                    return ''
                return self.node_lookup[node_id]


        def create_graph():
            """Creates a graph from saved GraphDef file and returns a saver."""
            # Creates graph from saved graph_def.pb.
            with tf.io.gfile.GFile(os.path.join(
                    FLAGS.model_dir, 'tensorflow_inception_graph.pb'),
                    'rb') as f:
                graph_def = tf.compat.v1.GraphDef()
                graph_def.ParseFromString(f.read())
                _ = tf.import_graph_def(graph_def, name='')


        def run_inference_on_image(image):
            """Runs inference on an image.

            Args:
              image: Image file name.

            Returns:
              Nothing
            """
            if not tf.io.gfile.exists(image):
                tf.logging.fatal('File does not exist %s', image)
            image_data =tf.io.gfile.GFile(image, 'rb').read()

            # Creates graph from saved GraphDef.
            create_graph()

            with tf.compat.v1.Session() as sess:
                # Some useful tensors:
                # 'softmax:0': A tensor containing the normalized prediction across
                #   1000 labels.
                # 'pool_3:0': A tensor containing the next-to-last layer containing 2048
                #   float description of the image.
                # 'DecodeJpeg/contents:0': A tensor containing a string providing JPEG
                #   encoding of the image.
                # Runs the softmax tensor by feeding the image_data as input to the graph.
                softmax_tensor = sess.graph.get_tensor_by_name('softmax:0')
                predictions = sess.run(softmax_tensor,{'DecodeJpeg/contents:0': image_data})


                sess.close()
                predictions = np.squeeze(predictions)

                # Creates node ID --> English string lookup.
                node_lookup = NodeLookup()

                top_k = predictions.argsort()[-FLAGS.num_top_predictions:][
                        ::-1]
                for node_id in top_k:
                    human_string = node_lookup.id_to_string(node_id)
                    score = predictions[node_id]*100
                    descript = human_string

            #return descript, score

            return "dummy",0


        parser = argparse.ArgumentParser()
        # classify_image_graph_def.pb:
        #   Binary representation of the GraphDef protocol buffer.
        # imagenet_synset_to_human_label_map.txt:
        #   Map from synset ID to a human readable string.
        # imagenet_2012_challenge_label_map_proto.pbtxt:
        #   Text representation of a protocol buffer mapping a label to synset ID.
        parser.add_argument(
            '--model_dir',
            type=str,
            default = os.path.join( os.path.dirname(__file__), 'files'),
            help="""\
          Path to classify_image_graph_def.pb,
          imagenet_synset_to_human_label_map.txt, and
          imagenet_2012_challenge_label_map_proto.pbtxt.\
          """
        )
        parser.add_argument(
            '--image_file',
            type=str,
            default='',
            help='Absolute path to image file.'
        )
        parser.add_argument(
            '--num_top_predictions',
            type=int,
            default=1,
            help='Display this many predictions.'
        )
        FLAGS, unparsed = parser.parse_known_args()
        image = (FLAGS.image_file if FLAGS.image_file else
                 os.path.join(FLAGS.model_dir, self.image_filename))

        if datas:
            self.animalname, self.probability =run_inference_on_image(image)
