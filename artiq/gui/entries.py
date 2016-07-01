import logging
from collections import OrderedDict

from PyQt5 import QtCore, QtGui, QtWidgets

from artiq.gui.tools import LayoutWidget, disable_scroll_wheel
from artiq.gui.scanwidget import ScanWidget


logger = logging.getLogger(__name__)


class _StringEntry(QtWidgets.QLineEdit):
    def __init__(self, argument):
        QtWidgets.QLineEdit.__init__(self)
        self.setText(argument["state"])
        def update(text):
            argument["state"] = text
        self.textEdited.connect(update)

    @staticmethod
    def state_to_value(state):
        return state

    @staticmethod
    def default_state(procdesc):
        return procdesc.get("default", "")


class _BooleanEntry(QtWidgets.QCheckBox):
    def __init__(self, argument):
        QtWidgets.QCheckBox.__init__(self)
        self.setChecked(argument["state"])
        def update(checked):
            argument["state"] = bool(checked)
        self.stateChanged.connect(update)

    @staticmethod
    def state_to_value(state):
        return state

    @staticmethod
    def default_state(procdesc):
        return procdesc.get("default", False)


class _EnumerationEntry(QtWidgets.QComboBox):
    def __init__(self, argument):
        QtWidgets.QComboBox.__init__(self)
        disable_scroll_wheel(self)
        choices = argument["desc"]["choices"]
        self.addItems(choices)
        idx = choices.index(argument["state"])
        self.setCurrentIndex(idx)
        def update(index):
            argument["state"] = choices[index]
        self.currentIndexChanged.connect(update)

    @staticmethod
    def state_to_value(state):
        return state

    @staticmethod
    def default_state(procdesc):
        if "default" in procdesc:
            return procdesc["default"]
        else:
            return procdesc["choices"][0]


class _NumberEntry(QtWidgets.QDoubleSpinBox):
    def __init__(self, argument):
        QtWidgets.QDoubleSpinBox.__init__(self)
        disable_scroll_wheel(self)
        procdesc = argument["desc"]
        scale = procdesc["scale"]
        self.setDecimals(procdesc["ndecimals"])
        self.setSingleStep(procdesc["step"]/scale)
        if procdesc["min"] is not None:
            self.setMinimum(procdesc["min"]/scale)
        else:
            self.setMinimum(float("-inf"))
        if procdesc["max"] is not None:
            self.setMaximum(procdesc["max"]/scale)
        else:
            self.setMaximum(float("inf"))
        if procdesc["unit"]:
            self.setSuffix(" " + procdesc["unit"])

        self.setValue(argument["state"]/scale)
        def update(value):
            argument["state"] = value*scale
        self.valueChanged.connect(update)

    @staticmethod
    def state_to_value(state):
        return state

    @staticmethod
    def default_state(procdesc):
        if "default" in procdesc:
            return procdesc["default"]
        else:
            return 0.0


class _NoScan(LayoutWidget):
    def __init__(self, procdesc, state):
        LayoutWidget.__init__(self)

        scale = procdesc["scale"]
        self.value = QtWidgets.QDoubleSpinBox()
        disable_scroll_wheel(self.value)
        self.value.setDecimals(procdesc["ndecimals"])
        if procdesc["global_min"] is not None:
            self.value.setMinimum(procdesc["global_min"]/scale)
        else:
            self.value.setMinimum(float("-inf"))
        if procdesc["global_max"] is not None:
            self.value.setMaximum(procdesc["global_max"]/scale)
        else:
            self.value.setMaximum(float("inf"))
        self.value.setSingleStep(procdesc["global_step"]/scale)
        if procdesc["unit"]:
            self.value.setSuffix(" " + procdesc["unit"])
        self.addWidget(QtWidgets.QLabel("Value:"), 0, 0)
        self.addWidget(self.value, 0, 1)

        self.value.setValue(state["value"]/scale)
        def update(value):
            state["value"] = value*scale
        self.value.valueChanged.connect(update)


class _RangeScan(LayoutWidget):
    def __init__(self, procdesc, state):
        LayoutWidget.__init__(self)

        scale = procdesc["scale"]

        def apply_properties(widget):
            widget.setDecimals(procdesc["ndecimals"])
            if procdesc["global_min"] is not None:
                widget.setMinimum(procdesc["global_min"]/scale)
            else:
                widget.setMinimum(float("-inf"))
            if procdesc["global_max"] is not None:
                widget.setMaximum(procdesc["global_max"]/scale)
            else:
                widget.setMaximum(float("inf"))
            if procdesc["global_step"] is not None:
                widget.setSingleStep(procdesc["global_step"]/scale)
            if procdesc["unit"]:
                widget.setSuffix(" " + procdesc["unit"])

        scanner = ScanWidget()
        disable_scroll_wheel(scanner)
        self.addWidget(scanner, 0, 0, -1, 1)

        start = QtWidgets.QDoubleSpinBox()
        start.setStyleSheet("QDoubleSpinBox {color:blue}")
        start.setMinimumSize(110, 0)
        start.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        disable_scroll_wheel(start)
        self.addWidget(start, 0, 1)

        npoints = QtWidgets.QSpinBox()
        npoints.setMinimum(1)
        npoints.setMaximum((1 << 31) - 1)
        disable_scroll_wheel(npoints)
        self.addWidget(npoints, 1, 1)

        stop = QtWidgets.QDoubleSpinBox()
        stop.setStyleSheet("QDoubleSpinBox {color:red}")
        stop.setMinimumSize(110, 0)
        disable_scroll_wheel(stop)
        self.addWidget(stop, 2, 1)

        apply_properties(start)
        apply_properties(stop)
        apply_properties(scanner)

        def update_start(value):
            state["start"] = value*scale
            scanner.setStart(value)

        def update_stop(value):
            state["stop"] = value*scale
            scanner.setStop(value)

        def update_npoints(value):
            state["npoints"] = value
            scanner.setNum(value)

        scanner.startChanged.connect(start.setValue)
        scanner.numChanged.connect(npoints.setValue)
        scanner.stopChanged.connect(stop.setValue)
        start.valueChanged.connect(update_start)
        npoints.valueChanged.connect(update_npoints)
        stop.valueChanged.connect(update_stop)
        scanner.setStart(state["start"]/scale)
        scanner.setNum(state["npoints"])
        scanner.setStop(state["stop"]/scale)


class _ExplicitScan(LayoutWidget):
    def __init__(self, state):
        LayoutWidget.__init__(self)

        self.value = QtWidgets.QLineEdit()
        self.addWidget(QtWidgets.QLabel("Sequence:"), 0, 0)
        self.addWidget(self.value, 0, 1)

        float_regexp = r"(([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)"
        regexp = "(float)?( +float)* *".replace("float", float_regexp)
        self.value.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(regexp)))

        self.value.setText(" ".join([str(x) for x in state["sequence"]]))
        def update(text):
            if self.value.hasAcceptableInput():
                state["sequence"] = [float(x) for x in text.split()]
        self.value.textEdited.connect(update)


class _ScanEntry(LayoutWidget):
    def __init__(self, argument):
        LayoutWidget.__init__(self)
        self.argument = argument

        self.stack = QtWidgets.QStackedWidget()
        self.addWidget(self.stack, 1, 0, colspan=4)

        procdesc = argument["desc"]
        state = argument["state"]
        self.widgets = OrderedDict()
        self.widgets["NoScan"] = _NoScan(procdesc, state["NoScan"])
        self.widgets["LinearScan"] = _RangeScan(procdesc, state["LinearScan"])
        self.widgets["RandomScan"] = _RangeScan(procdesc, state["RandomScan"])
        self.widgets["ExplicitScan"] = _ExplicitScan(state["ExplicitScan"])
        for widget in self.widgets.values():
            self.stack.addWidget(widget)

        self.radiobuttons = OrderedDict()
        self.radiobuttons["NoScan"] = QtWidgets.QRadioButton("No scan")
        self.radiobuttons["LinearScan"] = QtWidgets.QRadioButton("Linear")
        self.radiobuttons["RandomScan"] = QtWidgets.QRadioButton("Random")
        self.radiobuttons["ExplicitScan"] = QtWidgets.QRadioButton("Explicit")
        scan_type = QtWidgets.QButtonGroup()
        for n, b in enumerate(self.radiobuttons.values()):
            self.addWidget(b, 0, n)
            scan_type.addButton(b)
            b.toggled.connect(self._scan_type_toggled)

        selected = argument["state"]["selected"]
        self.radiobuttons[selected].setChecked(True)

    @staticmethod
    def state_to_value(state):
        selected = state["selected"]
        r = dict(state[selected])
        r["ty"] = selected
        return r

    @staticmethod
    def default_state(procdesc):
        scale = procdesc["scale"]
        state = {
            "selected": "NoScan",
            "NoScan": {"value": 0.0},
            "LinearScan": {"start": 0.0, "stop": 100.0*scale, "npoints": 10},
            "RandomScan": {"start": 0.0, "stop": 100.0*scale, "npoints": 10},
            "ExplicitScan": {"sequence": []}
        }
        if "default" in procdesc:
            default = procdesc["default"]
            ty = default["ty"]
            state["selected"] = ty
            if ty == "NoScan":
                state["NoScan"]["value"] = default["value"]
            elif ty == "LinearScan" or ty == "RandomScan":
                for d in state["LinearScan"], state["RandomScan"]:
                    d["start"] = default["start"]
                    d["stop"] = default["stop"]
                    d["npoints"] = default["npoints"]
            elif ty == "ExplicitScan":
                state["ExplicitScan"]["sequence"] = default["sequence"]
            else:
                logger.warning("unknown default type: %s", ty)
        return state

    def _scan_type_toggled(self):
        for ty, button in self.radiobuttons.items():
            if button.isChecked():
                self.stack.setCurrentWidget(self.widgets[ty])
                self.argument["state"]["selected"] = ty
                break


argty_to_entry = {
    "PYONValue": _StringEntry,
    "BooleanValue": _BooleanEntry,
    "EnumerationValue": _EnumerationEntry,
    "NumberValue": _NumberEntry,
    "StringValue": _StringEntry,
    "Scannable": _ScanEntry
}
