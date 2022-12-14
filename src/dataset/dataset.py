import os
import random
import numpy as np
from PIL import Image
from src.io import read_rgb
from torch.utils.data import Dataset
from typing import Callable, Dict, List, Tuple, Union

class TrainDataset(Dataset):
    
    EXTENSIONS = (
        "jpg",
        "jpeg",
        "png",
        "ppm",
        "bmp",
        "pgm",
        "tif",
        "tiff",
        "webp",
    )
    
    def __init__(
        self,
        root_dir: str,
        train: bool,
        class_map: Dict[int, Union[str, List[str]]],
        max_samples_per_class: int = None,
        random_samples: bool = False,
        transform: Callable = None,
    ) -> None:
        """Image Classification Dataset init (image folder dataset)

        Args:
            root_dir (str): root data dir
            train (bool): train mode
            class_map (Dict[int, Union[str, List[str]]], optional): class map {e.g. {0: 'class_a', 1: ['class_b', 'class_c']}}
            max_samples_per_class (int, optional): max number of samples for each class in the dataset. Defaults to None.
            random_samples (bool, optional): if selecting randomnly the max samples per class. Defaults to False.
            transform (Callable, optional): set of data transformations. Defaults to None.

        Raises:
            e: if something is found erroneous in the dataset
        """
        
        super().__init__()
        
        assert isinstance(class_map, dict), "class_map must be a Python dict"
        
        data_dir = os.path.join(root_dir, "train" if train else "val")
        # checking structure
        self.train = train
        try:
            self._sanity_check(
                data_dir=data_dir, 
                class_map=class_map
            )
        except Exception as e:
            raise e
        self.data_dir = data_dir
        self.class_map = class_map
        self.images, self.targets = self._load_samples(
            max_samples_per_class=max_samples_per_class,
            random_samples=random_samples
        )
        self.transform = transform
        self.stats()
        
    def _sanity_check(
        self,
        data_dir: str,
        class_map: Dict[int, Union[str, List[str]]]
    ):
        """Checks dataset structure

        Args:
            data_dir (str): data directory
            class_map (Dict[int, Union[str, List[str]]]): class map {e.g. {0: 'class_a', 1: ['class_b', 'class_c']}}
            
        Raises:
            FileNotFoundError: if the data folder is not right based on the structure in class_map
            FileExistsError: if some label does not have images in its folder

        """
        for k, labels in class_map.items():
            if not isinstance(labels, list):
                labels = [labels]
            for l in labels:
                label_dir =  os.path.join(data_dir, l)
                if not (os.path.exists(label_dir)):
                    raise FileNotFoundError(f"Folder {label_dir} does not exist") 
                if len(os.listdir(label_dir))==0:
                    raise FileExistsError(f"Folder {label_dir} is empty.")
                
        print(f"> {'Train' if self.train else 'Val/Test'} dataset sanity check OK")
    
    def _load_samples(
        self, 
        max_samples_per_class: int = None,
        random_samples: bool = False
    ) -> Tuple[List[str], List[int]]:
        """loads samples and targets

        Args:
            max_samples_per_class (int, optional): max samples per class. Dafaults to None.
            random_samples (bool, optional): if selecting randomnly the max samples per class. Defaults to False. Defaults to False.

        Returns:
            Tuple[List[str], List[int]]: images + targets
        """
        paths = []
        targets = []
        for c, labels in self.class_map.items():
            if isinstance(labels, str):
                labels = [labels]
            c_images, c_targets = [], []
            for label in labels:
                label_dir = os.path.join(self.data_dir, label)
                c_images += [os.path.join(label_dir, f) for f in os.listdir(label_dir) if f.split(".")[-1].lower() in self.EXTENSIONS]
            if max_samples_per_class is not None:
                if len(c_images) > max_samples_per_class:
                    print(f"> Images will be limited from {len(c_images)} to {max_samples_per_class} {'(selected randomnly) ' if random_samples else ''}for label {c} ({self.class_map[c]})")
                    if random_samples:
                        c_images = random.sample(c_images, max_samples_per_class)
                    else:
                        c_images = c_images[:max_samples_per_class]
            c_targets += [c] * len(c_images)

            paths += c_images
            targets += c_targets
        
        return paths, targets
    
    def stats(self):
        """prints stats of the dataset
        """
        unique, counts = np.unique(self.targets, return_counts=True)
        num_samples = len(self.targets)
        print(f" ----------- Dataset {'Train' if self.train else 'Val/Test'} Stats -----------")
        for k in range(len(unique)):
            classes = self.class_map[k]
            if isinstance(classes, str):
                classes = [classes]
            print(f"> {classes} : {counts[k]}/{num_samples} -> {100 * counts[k] / num_samples:.3f}%")
        print(f" -------------------------------------")
    
    def __getitem__(self, index) -> Tuple:
        
        img_path = self.images[index]
        target = self.targets[index]
        
        img = read_rgb(img_path)
        
        if self.transform is not None:
            img = self.transform(img)
        
        return img, target
            
    def __len__(self):
        return len(self.images)
    
class InferenceDataset(Dataset):
    
    EXTENSIONS = (
        "jpg",
        "jpeg",
        "png",
        "ppm",
        "bmp",
        "pgm",
        "tif",
        "tiff",
        "webp",
    )
    
    def __init__(
        self,
        root_dir: str,
        class_map: Dict[int, Union[str, List[str]]] = None,
        transform: Callable = None,
    ) -> None:
        """Image Classification Inference Dataset (a folder with images)

        Args:
            root_dir (str): root data dir (must be with train and val folders)
            class_map (Dict)
            transform (Callable, optional): set of data transformations. Defaults to None.

        Raises:
            FileNotFoundError: if something is found erroneous in the dataset
        """
        
        super().__init__()
        # checking structure
        try:
            self._sanity_check(
                root_dir=root_dir, 
                class_map=class_map
            )
        except Exception as e:
            raise e
        
        self.class_map = class_map
        self.data_dir = root_dir
        self.images, self.targets = self._load_samples()
        self.transform = transform
    
    def _sanity_check(
        self,
        root_dir: str,
        class_map: Dict[int, Union[str, List[str]]] = None
    ):
        """Checks dataset structure

        Args:
            root_dir (str): data directory
            class_map (Dict[int, Union[str, List[str]]]): class map {e.g. {0: 'class_a', 1: ['class_b', 'class_c']}}
            
        Raises:
            FileNotFoundError: if the data folder is not right based on the structure in class_map
            FileExistsError: if some label does not have images in its folder

        """
        if class_map is None:
            if not (os.path.exists(root_dir)):
                    raise FileNotFoundError(f"Folder {root_dir} does not exist") 
            images = [f for f in os.listdir(root_dir) if f.split(".")[-1].lower() in self.EXTENSIONS]
            if len(images) == 0:
                raise FileExistsError(f"Folder {root_dir} does not have images.")
        else:
            for k, labels in class_map.items():
                if not isinstance(labels, list):
                    labels = [labels]
                for l in labels:
                    label_dir =  os.path.join(root_dir, l)
                    if not (os.path.exists(label_dir)):
                        raise FileNotFoundError(f"Folder {label_dir} does not exist") 
                    if len(os.listdir(label_dir))==0:
                        raise FileExistsError(f"Folder {label_dir} is empty.")
                
        print(f"> Inference dataset sanity check OK")
    
    def _load_samples(self) -> Tuple[List[str], List[int]]:
        """loads image paths + targets for the dataset

        Returns:
           Tuple[List[str], List[int]]: images paths + targets (could be None)
        """
        
        if self.class_map is None:
            paths = [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f.split(".")[-1].lower() in self.EXTENSIONS]
            targets = [-1]*len(paths)
        else:
            paths, targets = [], []
            for c, labels in self.class_map.items():
                if isinstance(labels, str):
                    labels = [labels]
                c_images, c_targets = [], []
                for label in labels:
                    label_dir = os.path.join(self.data_dir, label)
                    c_images += [os.path.join(label_dir, f) for f in os.listdir(label_dir) if f.split(".")[-1].lower() in self.EXTENSIONS]
                c_targets += [c] * len(c_images)
                paths += c_images
                targets += c_targets
        
        return paths, targets
        
    def __getitem__(self, index) -> Image.Image:
        
        img_path = self.images[index]
        target = self.targets[index]
        
        img = read_rgb(img_path)
        
        if self.transform is not None:
            img = self.transform(img)
        
        return img, target
            
    def __len__(self):
        return len(self.images)
    
    
