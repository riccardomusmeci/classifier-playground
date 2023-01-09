import os
import torch
from typing import Dict, List, Tuple

class ModelCheckpoint:
    
    def __init__(
        self,
        output_dir: str,
        monitor: str = "acc/val",
        mode: str = "max",
        save_top_k: int = 5,
        patience: int = 10
    ) -> None:
        """Model checkpoint class to save checkpoints and monitoring them. 
        Filename for each checkpoint will be filled with metrics from Trainer.

        Args:
            output_dir (str): output dir where checkpoints folder will contain pth files.
            monitor (str, optional): metric to monitor. Defaults to "acc/val".
            mode (str, optional): mode to check metric to monitor. Defaults to "max".
            save_top_k (int, optional): how many top pth files to keep during training. Defaults to 5.
            patience (int, optional): how many epochs to wait before ending training if metric to monitor does not improve. Defaults to 10.
        """
        
        assert mode in ["max", "min"], f"Mode {mode} not supported. Choose between max or min."
        self.output_dir = os.path.join(output_dir, "checkpoints")
        os.makedirs(self.output_dir)
        self.monitor = monitor
        self.history: List[Tuple[int, int]] = [] # each el is a Tuple of (val, epoch)
        self.save_top_k = save_top_k
        self.mode = mode
        self.reverse = True if self.mode == "max" else False
        self.patience = patience
        
        # support fields
        self.patience_count = 0
        self.to_remove = None # an epoch will be saved here
    
    def _update_history_sequence(
        self,
        val: float,
        epoch: int,
        remove_last: bool
    ): 
        """updates history sequence

        Args:
            val (float): value to add
            epoch (int): current epoch
            remove_last (bool): remove last from history
        """

        if remove_last:
            self.to_remove = self.history[-1][1]
            self.history = self.history[:-1]
            
        self.history.append((val, epoch))
        self.history = sorted(self.history, reverse=self.reverse, key=lambda x: x[0])
        self.patience_count = 0
      
    @property  
    def best_val(self) -> float:
        """returns best value of history sequence

        Returns:
            float: best value
        """
        if len(self.history) == 0: 
            return None
        return sorted(self.history, reverse=self.reverse, key=lambda x: x[0])[0][0]
    
    def _update_history(
        self,
        val: float,
        epoch: int
    ):
        """updates history

        Args:
            val (float): metric val to evaluate 
            epoch (int): epoch to evaluate
        """
        
        if len(self.history) < self.save_top_k:
            self._update_history_sequence(
                val=val,
                epoch=epoch,
                remove_last=False
            )
            print(f"Epoch {epoch} with best model with {self.monitor}={val:.4f}. Best model is at {self.monitor}={self.best_val:.4f}")
        else:
            # checking for history full
            to_update = True
            if self.mode == "max" and val<min(self.history, key=lambda x: x[0])[0]:
                to_update = False
            elif self.mode == "min" and val>max(self.history, key=lambda x: x[0])[0]:
                to_update = False
            
            if not to_update:
                print(f"Epoch {epoch} was not between best models with {self.monitor}={val:.4f}. Current best model interval is {self.monitor}={self.best_val:.4f}")
                self.patience_count += 1
            else:
                self._update_history_sequence(
                    val=val,
                    epoch=epoch,
                    remove_last=True
                )
                          
    @property        
    def patience_over(
        self
    ) -> bool:
        """checks if patience is over

        Returns:
            bool: True if patience over, False otherwise
        """
        return self.patience_count >= self.patience

    def _create_filename(
        self,
        epoch: int,
        metrics: Dict[str, float]
    ) -> str:
        """creates pth filename

        Args:
            epoch (int): epoch
            metrics (Dict[str, float]): metrics dict

        Returns:
            str: pth filename
        """
        base_filename = f"epoch={epoch}-"
        for i, k in enumerate(sorted(list(metrics.keys()))):
            if (i+1)==len(metrics): 
                sep = ""
            else: 
                sep = "-"
            base_filename += f"{k}={metrics[k]:.4f}{sep}"
        return f"{base_filename}.pth"
     
    def save(
        self,
        epoch: int,
        metrics: Dict[str, float],
        state_dict: Dict
    ):
        """saves pth file and removes old worst one if needed

        Args:
            epoch (int): current epoch
            metrics (Dict[str, float]): metrics to add in filename
            state_dict (Dict): model state dict
        """
        pth_filename = self._create_filename(
            epoch=epoch,
            metrics=metrics
        )
        
        if len(self.history) == self.save_top_k:
            for f in os.listdir(self.output_dir):
                if self.to_remove is not None:
                    if f.startswith(f"epoch={self.to_remove}"):
                        os.remove(os.path.join(self.output_dir, f))
        try:
            torch.save(
                state_dict,
                os.path.join(self.output_dir, pth_filename)
            )
            print(f"Saved model pth file ({pth_filename}) in checkpoints folder.")
        except Exception as e:
            print(f"[ERROR] Error while saving model. Error {e}.")
           
    def step(
        self,
        epoch: int,
        metrics: Dict[str, float],
        state_dict: Dict
    ):
        """updates model checkpoint data and save pth file if needed

        Args:
            epoch (int): current epoch
            metrics (Dict[str, float]): validation metrics
            state_dict (Dict): model state dict
        """
        
        self._update_history(
            val=metrics[self.monitor],
            epoch=epoch
        )
        
        # it means one of best models just added
        if self.patience_count == 0:
            self.save(
                epoch=epoch,
                metrics=metrics,
                state_dict=state_dict
            )
        
        
        

    
   
        
        
        