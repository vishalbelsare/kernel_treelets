import inspect
import itertools

import numpy as np
from sklearn.svm import SVC

from kernel_treelets import kernel_treelets

SVCkeys = inspect.signature(SVC.__init__).parameters.keys()


class kernel_treelets_clustering(kernel_treelets):
	def __init__ (self, kernel=False, number_of_clusters=0, max_sample=500, label_type=None, verbose=False, **kwargs):
		super().__init__(kernel, verbose=verbose, **kwargs)
		self.max_sample = max_sample
		self.tiny_cluster_number = 0
		self.label_type = label_type

		if number_of_clusters is 0:  # Auto-find clust num
			self.number_of_clusters = 2
			self.clustnum_estimate = True
		else:
			self.number_of_clusters = number_of_clusters
			self.clustnum_estimate = False

		# Output Variables Initialization
		self.dataset = None
		self.samp_dataset = None
		self.tree = None
		self.sample_index = None
		self.sample_labels = None
		self._labels_ = None
		self.svm = None
		self.raw_dataset = None

	def fit (self, X, k=-1):
		X = np.asmatrix(X)
		if X.shape[0] <= self.max_sample:  # small dataset
			self.dataset = X
			super().fit(self.dataset, k)

			# clustering on dataset
			self.tree = self._trl.tree
			if self.clustnum_estimate:
				self.find_clust_num(self._trl.dendrogram_list)

			self._labels_ = self.get_labels()
			self.sample_labels = np.array(self._labels_, copy=True)

		else:  # large dataset
			self.raw_dataset = X  # origional copy

			# draw a small sample
			self.sample_index = np.sort(np.random.choice(self.raw_dataset.shape[0], self.max_sample, replace=False))
			self.dataset = self.raw_dataset[self.sample_index, :]

			# build model on small sample
			self.fit(self.dataset, k)
			coef_dict = {key: self.coef_dict[key] for key in self.coef_dict if key in SVCkeys}

			temp = np.unique(self._labels_, return_counts=True)
			valid_labels = np.isin(self._labels_, temp[0][np.argsort(temp[1])][-self.number_of_clusters:])

			self.dataset = self.dataset[valid_labels]
			self._labels_ = self._labels_[valid_labels]

			# generalize to large sample with SVM
			try:
				self.svm = SVC(kernel=self.kernel_name, **coef_dict)
				self.svm.fit(self.dataset, self._labels_)
			except ValueError:
				self.svm = SVC()
				self.svm.fit(self.dataset, self._labels_)
			self._labels_ = self.svm.predict(self.raw_dataset)

	def find_clust_num (self, dendrogram_list):
		# find the first gap with 1
		for i in range(1, self.n - 1):
			if np.abs(dendrogram_list[i - 1] - dendrogram_list[i]) > 1:
				self.number_of_clusters = len(self) - i
				return self.number_of_clusters

	def get_labels (self):
		temp_labels = np.arange(self.n)
		for i in range(self.n - self.number_of_clusters - 1, -1, -1):
			temp_labels[self.tree[i][1]] = temp_labels[self.tree[i][0]]
		return temp_labels

	@property
	def labels_ (self):
		if self.label_type is None:
			pass
		elif self.label_type == int:
			temp_dict = {v: k for k, v in enumerate(np.unique(self._labels_), 0)}
			self._labels_ = np.vectorize(temp_dict.__getitem__)(self._labels_)
		else:
			temp_dict = {v: k for k, v in enumerate(np.unique(self._labels_), 0)}
			temp_list = itertools.islice(self.label_type, len(temp_dict))
			tempf = lambda x: temp_list[temp_dict[x]]
			self._labels_ = np.apply_along_axis(np.vectorize(tempf), 0, self._labels_)

		return self._labels_

	def __len__ (self):
		return self.dataset.shape[0]


KT_clustering = kernel_treelets_clustering
