"""
* *IntelComp H2020 project*

Class that defines the subwindow for the Interactive Topic Model Trainer App for the selection of the preprocessing settings prior to topic modeling.

"""

import configparser

import numpy as np
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QLabel
from PyQt6.uic import loadUi
from src.gui.utils import utils
from src.gui.utils.constants import Constants


class PreprocessingWindow(QtWidgets.QDialog):

    def __init__(self, tm):
        """
        Initializes the application's subwindow from which the user select the topic modeling's preprocessing settings.

        Parameters
        ----------
        tm : TaskManager
            TaskManager object associated with the project
        """

        super(PreprocessingWindow, self).__init__()

        # Load UI
        # #####################################################################
        loadUi("src/gui/uis/select_preproc_settings.ui", self)

        ########################################################################
        # ATTRIBUTES
        ########################################################################
        self.tm = tm
        self.preproc_settings = None

        ########################################################################
        # Widgets initial configuration
        ########################################################################
        # Configure tables
        utils.configure_table_header(Constants.PREPROC_TABLES, self)

        # Initialize checkboxes
        self.preproc_checkboxes_params = []
        for id_check in np.arange(Constants.NR_PARAMS_PREPROC):
            checkbox_name = "checkBox_preproc_" + str(id_check + 1) + "_good"
            checkbox_widget = self.findChild(QLabel, checkbox_name)
            self.preproc_checkboxes_params.append(checkbox_widget)
            checkbox_name = "checkBox_preproc_" + str(id_check + 1) + "_bad"
            checkbox_widget = self.findChild(QLabel, checkbox_name)
            self.preproc_checkboxes_params.append(checkbox_widget)
        for checkbox in self.preproc_checkboxes_params:
            checkbox.hide()

        self.set_settings()
        self.tabWidget_preproc.tabBar().setExpanding(True)

        ########################################################################
        # Connect buttons
        ########################################################################
        self.pushButton_select_params.clicked.connect(
            self.clicked_pushButton_select_params)

    def set_settings(self):
        """Sets the value of the default preprocessing settings in the corresponding widgets.
        """
        # Get config object
        cf = configparser.ConfigParser()
        cf.read(self.tm.p2config_dft)

        # Fill default values of preprocessing settings
        self.lineEdit_min_lemas.setText(str(cf.get('Preproc', 'min_lemas')))
        self.lineEdit_no_below.setText(str(cf.get('Preproc', 'no_below')))
        self.lineEdit_no_above.setText(str(cf.get('Preproc', 'no_above')))
        self.lineEdit_keep_n.setText(str(cf.get('Preproc', 'keep_n')))

        # Fill table of stopwords with the available lists of stopwords
        self.sw_lists = self.tm.listWdListsByType(self.table_available_stopwords, "stopwords")

        # Add checkboxes in the first column so the user can select the stopwords to use
        utils.add_checkboxes_to_table(self.table_available_stopwords, 0)

        # Fill table of stopwords with the available lists of equivalences
        self.eq_lists = self.tm.listWdListsByType(
            self.table_available_equivalences, "equivalences")

        # Add checkboxes in the first column so the user can select the stopwords to use
        utils.add_checkboxes_to_table(self.table_available_equivalences, 0)

        return

    def clicked_pushButton_select_params(self):
        """It controls the clicking of the 'pushButton_select_params'. Once the button is clicked, each of the parameters chosen is read from the window's widget and saved in a dictionary structure. After the preprocessing parameter selection completion, the window is closed.
        """

        min_lemas = int(self.lineEdit_min_lemas.text())
        no_below = int(self.lineEdit_no_below.text())
        no_above = float(self.lineEdit_no_above.text())
        keep_n = int(self.lineEdit_keep_n.text())

        # Get ids of the stopword lists that are going to be used
        StwLists_items = []
        for i in range(self.table_available_stopwords.rowCount()):
            item = self.table_available_stopwords.item(
                i, 0)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                StwLists_items.append(i)

        # Get ids of the equivalences lists that are going to be used
        EqLists_items = []
        for i in range(self.table_available_equivalences.rowCount()):
            item = self.table_available_equivalences.item(
                i, 0)
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                EqLists_items.append(i)
        
        StwLists = [self.sw_lists[int(el)] for el in StwLists_items]
        EqLists = [self.eq_lists[int(el)] for el in EqLists_items]

        self.preproc_settings = {
            "min_lemas": min_lemas,
            "no_below": no_below,
            "no_above": no_above,
            "keep_n": keep_n,
            "stopwords": StwLists,
            "equivalences": EqLists
        }

        # Hide window
        self.hide()

        return
