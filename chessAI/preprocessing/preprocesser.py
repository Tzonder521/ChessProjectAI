import pandas as pd
import numpy as np
import threading
import multiprocessing
import os
from sklearn.model_selection import train_test_split
from chessAI.preprocessing.gameMatricesCreation import create_game_matrices_one_chunk_games

"""This module provides the Preprocesser class"""

class Preprocesser():
    
    """Preprocess dataframe from the scraper
    
    :param _df_games: dataframe from the scraper with columns pgn_text and is_white_win
    :type _df_games: pd.DataFrame
    
    :param _nb_white_moves_done: number of white moves in the dataset
    :type _nb_white_moves_done: integer
    
    :param _nb_black_moves_done: number of black moves in the dataset
    :type _nb_black_moves_done: integer
    """
    
    def __init__(self, df_games, nb_white_moves_done=0, nb_black_moves_done=0):
        
        self._df_games = df_games
        self._nb_games_done = 0
        self._nb_white_moves_done = nb_white_moves_done
        self._nb_black_moves_done = nb_black_moves_done
        self._n_chunk = 1
        self._lock_df_games = threading.Lock()
        self._lock_nb_games_done = threading.Lock()
        self._lock_nb_moves_done = threading.Lock()
        self._lock_n_chunk = threading.Lock()     
        
        
    def get_a_chunk(self, chunk_size):
        
        """Return a chunk of self._df_games and drop it from the original dataframe. The size of the chunk is :
            - chunk_size if the size of the df is superior or equal to chunk_size
            - the size of the df if its size is inferior but not 0
            - an empty df else
            
        :param chunk_size: size of the chunk
        :type chunk_size: integer
        
        :return df_chunk: a chunk of self._df_games
        :rtype df_chunk: pd.DataFrame()
        """
        
        # Use lock to ensure thread safety access to the original df
        with self._lock_df_games:
            # If df is empty, df_chunk is empty
            if self._df_games.shape[0] == 0: 
                df_chunk = pd.DataFrame()
            else:
                # If the size of df is superior or equal to chunk_size, df_chunk is the last chunk_size row and drop it from original dataframe
                if self._df_games.shape[0] >= chunk_size:
                    df_chunk = self._df_games[self._df_games.shape[0] - chunk_size:self._df_games.shape[0]].copy()
                    self._df_games.drop(index=[x for x in range(self._df_games.shape[0] - chunk_size, self._df_games.shape[0])], inplace=True)
                # Else df_chunk is the rest of the original df
                else:
                    df_chunk = self._df_games[0:self._df_games.shape[0]].copy()
                    self._df_games.drop(index=[x for x in range(0, self._df_games.shape[0])], inplace=True)
                    
        return df_chunk
        
        
    def thread_create_game_matrices_chunks(self, chunk_size, nb_games, path_temp):
        
        """Thread method for the creation of game matrices chunks. It will take chunks in self._df_games of size chunk_size and will create comrpessed numpy array backup in the temporary directory given with path_temp
        
        :param chunk_size: the size of the chunks to process.
        :type chunk_size: integer
        
        :param nb_games: the number of games in self._df_games (use to give achievement informations)
        :type nb_games: integer
        
        :param path_temp: the path of the temporary directory to use to stock chunks matrices compressed
        :type path_temp: string
        """
        
        nb_moves_done = 0
        
        # Get a chunk of data
        df_chunk = self.get_a_chunk(chunk_size)
        
        # Iterate while there are data in self._df_games
        while df_chunk.shape[0] > 0:
            
            # Create game matrices
            matrices_white_1_chunk, matrices_white_2_chunk, matrices_white_3_chunk, matrices_white_4_chunk, \
            matrices_black_1_chunk, matrices_black_2_chunk, matrices_black_3_chunk, matrices_black_4_chunk, \
            y_white_chunk, y_black_chunk = create_game_matrices_one_chunk_games(df_chunk)

            # Get the number of the actual chunk and update (+1)
            with self._lock_n_chunk:
                n_chunk = self._n_chunk
                self._n_chunk += 1
            
            # Save chunk in path temp
            np.savez_compressed(path_temp + 'X_white_1/' + 'X_white_1_chunk_' + str(n_chunk), matrices=matrices_white_1_chunk)
            np.savez_compressed(path_temp + 'X_white_2/' + 'X_white_2_chunk_' + str(n_chunk), matrices=matrices_white_2_chunk)
            np.savez_compressed(path_temp + 'X_white_3/' + 'X_white_3_chunk_' + str(n_chunk), matrices=matrices_white_3_chunk)
            np.savez_compressed(path_temp + 'X_white_4/' + 'X_white_4_chunk_' + str(n_chunk), matrices=matrices_white_4_chunk)
            np.savez_compressed(path_temp + 'X_black_1/' + 'X_black_1_chunk_' + str(n_chunk), matrices=matrices_black_1_chunk)
            np.savez_compressed(path_temp + 'X_black_2/' + 'X_black_2_chunk_' + str(n_chunk), matrices=matrices_black_2_chunk)
            np.savez_compressed(path_temp + 'X_black_3/' + 'X_black_3_chunk_' + str(n_chunk), matrices=matrices_black_3_chunk)
            np.savez_compressed(path_temp + 'X_black_4/' + 'X_black_4_chunk_' + str(n_chunk), matrices=matrices_black_4_chunk)
            np.savez_compressed(path_temp + 'y_white/' + 'y_white_chunk_' + str(n_chunk), matrices=y_white_chunk)
            np.savez_compressed(path_temp + 'y_black/' + 'y_black_chunk_' + str(n_chunk), matrices=y_black_chunk)
            
            # Update nb of white and black move total
            with self._lock_nb_moves_done:
                self._nb_white_moves_done += y_white_chunk.shape[0]
                self._nb_black_moves_done += y_black_chunk.shape[0]
            
            # Update achievement
            with self._lock_nb_games_done:
                self._nb_games_done += df_chunk.shape[0]
                print('Preprocessing: ' + str(self._nb_games_done) + '/' + str(nb_games) + ' done', end='\r')
                
            # Get a chunk of data for next iteration
            df_chunk = self.get_a_chunk(chunk_size)

            
    def thread_unify_chunk(self, target, path_temp):
        
        """Unify the compressed numpy array chunks stock in the directory path_temp into a memmapped numpy array in the directory path_temp. Unify the array specified by target (ex: 'X_white_1', 'X_black_4', 'y_white' ...)
        
        :param target: the type of array to unify (X_{black or white}_{1 to 4} or y_{black or white})
        :type target: string
        
        :param path_temp: path of the temporary directory where are stocked the compressed numpy array chunks
        :type path_temp: string
        """
        
        # Choose the shape of the matrice and the dtype according to the target
        if target == 'X_white_1':
            shape_matrice = (self._nb_white_moves_done, 8, 8, 12)
            dtype = bool
        elif target == 'X_white_2':
            shape_matrice = (self._nb_white_moves_done, 8, 8, 6)
            dtype = int
        elif target == 'X_white_3':
            shape_matrice = (self._nb_white_moves_done, 8, 8, 4)
            dtype = float
        elif target == 'X_white_4':
            shape_matrice = (self._nb_white_moves_done, 8, 8, 2)
            dtype = float
        elif target == 'X_black_1':
            shape_matrice = (self._nb_black_moves_done, 8, 8, 12)
            dtype = bool
        elif target == 'X_black_2':
            shape_matrice = (self._nb_black_moves_done, 8, 8, 6)
            dtype = int
        elif target == 'X_black_3':
            shape_matrice = (self._nb_black_moves_done, 8, 8, 4)
            dtype = float
        elif target == 'X_black_4':
            shape_matrice = (self._nb_black_moves_done, 8, 8, 2)
            dtype = float
        elif target == 'y_white':
            shape_matrice = (self._nb_white_moves_done,)
            dtype = bool
        elif target == 'y_black':
            shape_matrice = (self._nb_black_moves_done,)
            dtype = bool
                    
        # Read the name of the files (which are the chunk for the given target)
        files = os.listdir(path_temp + target + '/')
        # Create mapped matrices
        matrices = np.memmap(path_temp + target + '.dat', dtype=dtype, mode='w+', shape=shape_matrice)
        
        index_start = 0
        
        # Iterate over chunks: load the chunk and add it to the mapped matrices
        for file in files:
            matrices_chunk = np.load(path_temp + target + '/' + file)['matrices']
            index_stop = index_start + matrices_chunk.shape[0]
            matrices[index_start:index_stop] = matrices_chunk
            index_start = index_stop
            
        # Delete from RAM
        del matrices
            
        # Remove chunks
        for file in files:
            os.remove(path_temp + target + '/' + file)
            
        # Remove the directory
        os.rmdir(path_temp + target + '/')
        
        
    def split_dataset(self, path_temp='./temp/', path_data='./data/', size_validation=0.2, random_state=42):
        
        """Split the dataset into a part for train/test and a part for validation.

        :param path_temp: path used as temporary directory. Default: './temp/'
        :type path_temp: string
        
        :param path_data: path used as data directory to save final data. Default: './data/'
        :type path_data: string
        
        :param size_validation: size of the validation set (between 0 and 1). Default: 0.2
        :type size_validation: float
        
        :param random_state: number for random initialisation. Default: 42
        :type random_state: integer
        """
        
        targets = ['X_white_1', 'X_white_2', 'X_white_3', 'X_white_4', 'X_black_1', 'X_black_2', 'X_black_3', 'X_black_4', 'y_white', 'y_black']
        
        # Initialize the random seed to reproductibility
        np.random.seed(random_state)

        # Create index from 0 to last move
        index_white = np.arange(0, self._nb_white_moves_done)
        index_black = np.arange(0, self._nb_black_moves_done)
        
        # Shuffle the index
        np.random.shuffle(index_white)
        np.random.shuffle(index_black)
        
        # Compute the number of moves in validation set
        nb_val_white = int(size_validation * self._nb_white_moves_done)
        nb_val_black = int(size_validation * self._nb_black_moves_done)
        
        # Split the index between validation and training
        val_index_white = index_white[:nb_val_white]
        train_index_white = index_white[nb_val_white:]
        val_index_black = index_black[:nb_val_black]
        train_index_black = index_black[nb_val_black:]
        
        # Iterate over targets
        for target in targets:
            # Choose parameters regarding the target
            if target == 'X_white_1':
                dtype = bool
                shape_matrice = (self._nb_white_moves_done, 8, 8, 12)
                shape_matrice_val = (nb_val_white, 8, 8, 12)
                shape_matrice_train = (self._nb_white_moves_done - nb_val_white, 8, 8, 12)
                val_index = val_index_white
                train_index = train_index_white
            elif target == 'X_white_2':
                dtype = int
                shape_matrice = (self._nb_white_moves_done, 8, 8, 6)
                shape_matrice_val = (nb_val_white, 8, 8, 6)
                shape_matrice_train = (self._nb_white_moves_done - nb_val_white, 8, 8, 6)
                val_index = val_index_white
                train_index = train_index_white
            elif target == 'X_white_3':
                dtype = float
                shape_matrice = (self._nb_white_moves_done, 8, 8, 4)
                shape_matrice_val = (nb_val_white, 8, 8, 4)
                shape_matrice_train = (self._nb_white_moves_done - nb_val_white, 8, 8, 4)
                val_index = val_index_white
                train_index = train_index_white
            elif target == 'X_white_4':
                dtype = float
                shape_matrice = (self._nb_white_moves_done, 8, 8, 2)
                shape_matrice_val = (nb_val_white, 8, 8, 2)
                shape_matrice_train = (self._nb_white_moves_done - nb_val_white, 8, 8, 2)
                val_index = val_index_white
                train_index = train_index_white
            elif target == 'y_white':
                dtype = bool
                shape_matrice = (self._nb_white_moves_done, )
                shape_matrice_val = (nb_val_white, )
                shape_matrice_train = (self._nb_white_moves_done - nb_val_white, )
                val_index = val_index_white
                train_index = train_index_white
            elif target == 'X_black_1':
                dtype = bool
                shape_matrice = (self._nb_black_moves_done, 8, 8, 12)
                shape_matrice_val = (nb_val_black, 8, 8, 12)
                shape_matrice_train = (self._nb_black_moves_done - nb_val_black, 8, 8, 12)
                val_index = val_index_black
                train_index = train_index_black
            elif target == 'X_black_2':
                dtype = int
                shape_matrice = (self._nb_black_moves_done, 8, 8, 6)
                shape_matrice_val = (nb_val_black, 8, 8, 6)
                shape_matrice_train = (self._nb_black_moves_done - nb_val_black, 8, 8, 6)
                val_index = val_index_black
                train_index = train_index_black
            elif target == 'X_black_3':
                dtype = float
                shape_matrice = (self._nb_black_moves_done, 8, 8, 4)
                shape_matrice_val = (nb_val_black, 8, 8, 4)
                shape_matrice_train = (self._nb_black_moves_done - nb_val_black, 8, 8, 4)
                val_index = val_index_black
                train_index = train_index_black
            elif target == 'X_black_4':
                dtype = float
                shape_matrice = (self._nb_black_moves_done, 8, 8, 2)
                shape_matrice_val = (nb_val_black, 8, 8, 2)
                shape_matrice_train = (self._nb_black_moves_done - nb_val_black, 8, 8, 2)
                val_index = val_index_black
                train_index = train_index_black
            elif target == 'y_black':
                dtype = bool
                shape_matrice = (self._nb_black_moves_done, )
                shape_matrice_val = (nb_val_black, )
                shape_matrice_train = (self._nb_black_moves_done - nb_val_black, )
                val_index = val_index_black
                train_index = train_index_black
                            
            # Read the matrices
            matrices = np.memmap(path_temp + target + '.dat', dtype=dtype, mode='r', shape=shape_matrice)
            # Create new matrices for validation and training set
            matrices_val = np.memmap(path_data + target + '_val.dat', dtype=dtype, mode='w+', shape=shape_matrice_val)
            matrices_train = np.memmap(path_data + target + '_tuning.dat', dtype=dtype, mode='w+', shape=shape_matrice_train)
            
            # Assign value to matrices
            matrices_val[:] = matrices[val_index]
            matrices_train[:] = matrices[train_index]
            
            # Delete from RAM
            del matrices
            del matrices_val
            del matrices_train
            
            # Delete from disk
            os.remove(path_temp + target + '.dat')
            
            print('Preprocessing: ' + target + ' split done               ', end='\r')
            
        print('Preprocessing: all splits done                      ', end='\r')
            
            
    def create_game_matrices_chunks(self, chunk_size=100, path_temp='./temp/'):
        
        """Create game matrix chunks in path_temp using the df of games for 4 methods.
        
        :param chunk_size: size of the chunks of dataframe to preprocess. If memory problems, decrease this number. Default: 100
        :type chunk_size: integer
        
        :param path_temp: path used as temporary directory to work with chunk. Default: './temp/'
        :type path_temp: string
        """
        
        threads_chunk = []
        n_core = multiprocessing.cpu_count()
        targets = ['X_white_1', 'X_white_2', 'X_white_3', 'X_white_4', 'X_black_1', 'X_black_2', 'X_black_3', 'X_black_4', 'y_white', 'y_black']
        nb_games = self._df_games.shape[0]
        
        # Reset index (usefull if the given df is a fragment of a df)
        self._df_games.reset_index(drop=True, inplace=True)
        
        # Create temp subdirectory
        for target in targets:
            if not os.path.exists(path_temp + target + '/'):
                os.makedirs(path_temp + target + '/')
        
        # Create and start thread to do the task of martices creation
        for n_thread in range(0, n_core):
            threads_chunk.append(threading.Thread(target=self.thread_create_game_matrices_chunks, args=(chunk_size, nb_games, path_temp, )))
            threads_chunk[n_thread].start()
            
        # Wait the end of workers
        for thread in threads_chunk:
            thread.join()
            
            
    def unify_chunk(self, path_temp='./temp/'):
        
        """Unify the chunk create by create_game_matrices_chunks
        
        :param path_temp: path used as temporary directory to work with chunk. Default: './temp/'
        :type path_temp: string
        """
        
        targets = ['X_white_1', 'X_white_2', 'X_white_3', 'X_white_4', 'X_black_1', 'X_black_2', 'X_black_3', 'X_black_4', 'y_white', 'y_black']
        threads_unify = []
        
        # Create and start thread to do the task of unify matrices
        for target in targets:
            thread_unify = threading.Thread(target=self.thread_unify_chunk, args=(target, path_temp, ))
            thread_unify.start()
            threads_unify.append(thread_unify)
            
        # Wait the end of workers
        for thread_unify in threads_unify:
            thread_unify.join()
            
        print('Preprocessing: unification done                 ', end='\r')