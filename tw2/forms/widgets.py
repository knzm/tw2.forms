import tw2.core as twc, re, itertools, webob

#--
# Basic Fields
#--
class FormField(twc.Widget):
    name = twc.Variable('dom name', request_local=False, attribute=True, default=property(lambda s: s._compound_id(), lambda s, v: 1))


class InputField(FormField):
    type = twc.Variable('Type of input field', default=twc.Required, attribute=True)
    value = twc.Param(attribute=True)
    template = "genshi:tw2.forms.templates.input_field"


class TextField(InputField):
    size = twc.Param('Size of the text field', default=None, attribute=True)
    maxlength = twc.Param('Maximum length of input', default=None, attribute=True)
    type = 'text'


class TextArea(FormField):
    rows = twc.Param('Number of rows', default=None, attribute=True)
    cols = twc.Param('Number of columns', default=None, attribute=True)
    template = "genshi:tw2.forms.templates.textarea"


class HiddenField(InputField):
    type = 'hidden'


class LabelHiddenField(InputField):
    """
    A hidden field, with a label showing its contents.
    """
    type = 'hidden'
    template = "genshi:tw2.forms.templates.label_hidden"


class CheckBox(InputField):
    type = "checkbox"
    validator = twc.BoolValidator
    def prepare(self):
        super(CheckBox, self).prepare()
        if 'attrs' not in self.__dict__:
            self.attrs = self.attrs.copy()
        self.attrs['checked'] = 'true' if self.value else None
        self.value = None


class RadioButton(InputField):
    type = "radio"


class PasswordField(InputField):
    type = 'password'


class FileField(InputField):
    type = "file"


class Button(InputField):
    """Generic button. You can override the text using :attr:`value` and define
    a JavaScript action using :attr:`attrs['onclick']`.
    """
    type = "button"
    id = None


class SubmitButton(Button):
    """Button to submit a form."""
    type = "submit"
    @classmethod
    def post_define(cls):
        if cls.id_elem == 'submit':
            raise twc.ParameterError("A SubmitButton cannot have the id 'submit'")


class ResetButton(Button):
    """Button to clear the values in a form."""
    type = "reset"


class ImageButton(twc.Link, InputField):
    type = "image"
    width = twc.Param('Width of image in pixels', attribute=True, default=None)
    height = twc.Param('Height of image in pixels', attribute=True, default=None)
    alt = twc.Param('Alternate text', attribute=True, default='')
    src = twc.Variable(attribute=True)

    def prepare(self):
        super(ImageButton, self).prepare()
        self.src = self.link
        self.attrs['src'] = self.src # TBD: hack!

#--
# Selection fields
#--
class SelectionField(FormField):
    """
    Base class for single and multiple selection fields.

    The `options` parameter must be an interable; it can take several formats:

     * A list of values, e.g. ['', 'Red', 'Blue']
     * A list of (code, value) tuples, e.g.
       [(0, ''), (1, 'Red'), (2, 'Blue')]
     * A mixed list of values and tuples. If the code is not specified, it
       defaults to the value. e.g. ['', (1, 'Red'), (2, 'Blue')]
     * A list of groups, e.g.
        [('group', ['', (1, 'Red'), (2, 'Blue')]),
         ('group2', ['', 'Pink', 'Yellow'])]
    """

    options = twc.Param('Options to be displayed')

    selected_verb = twc.Variable(default='selected')
    field_type = twc.Variable()
    multiple = twc.Variable(default=False)
    grouped_options = twc.Variable()

    def prepare(self):
        super(SelectionField, self).prepare()
        grouped_options = []
        options = []
        counter = itertools.count(0)
        # TBD: if displaying errors, validate value
        value = self.value
        if self.multiple and not value:
            value = []
        for optgroup in self._iterate_options(self.options):
            xxx = []
            if isinstance(optgroup[1], (list,tuple)):
                group = True
                optlist = optgroup[1][:]
            else:
                group = False
                optlist = [optgroup]
            for option in self._iterate_options(optlist):
                if len(option) is 2:
                    option_attrs = {}
                elif len(option) is 3:
                    option_attrs = dict(option[2])
                option_attrs['value'] = option[0]
                if self.field_type:
                    option_attrs['type'] = self.field_type
                    # TBD: These are only needed for SelectionList
                    option_attrs['name'] = self._compound_id()
                    option_attrs['id'] = self._compound_id() + ':' + str(counter.next())
                if ((self.multiple and option[0] in value) or
                        (not self.multiple and option[0] == value)):
                    option_attrs[self.selected_verb] = self.selected_verb

                xxx.append((option_attrs, option[1]))
            options.extend(xxx)
            if group:
                grouped_options.append((optgroup[0], xxx))
        # options provides a list of *flat* options leaving out any eventual
        # group, useful for backward compatibility and simpler widgets
        # TBD: needed?
        self.options = options
        self.grouped_options = grouped_options if grouped_options else [(None, options)]


    def _iterate_options(self, optlist):
        for option in optlist:
            if not isinstance(option, (tuple,list)):
                yield (option, option)
            else:
                yield option


class SingleSelectField(SelectionField):
    template = "genshi:tw2.forms.templates.select_field"


class MultipleSelectField(SelectionField):
    size = twc.Param('Number of visible options', default=None, attribute=True)
    multiple = twc.Param(default=True, attribute=True)
    template = "genshi:tw2.forms.templates.select_field"


class SelectionList(SelectionField):
    selected_verb = "checked"
    template = "genshi:tw2.forms.templates.selection_list"

class RadioButtonValidator(twc.Validator):
    msgs = {
        'required': 'Please pick one'
    }

class CheckBoxValidator(twc.Validator):
    msgs = {
        'required': 'Please pick at least one'
    }

class RadioButtonList(SelectionList):
    field_type = "radio"
    validator = RadioButtonValidator()

class CheckBoxList(SelectionList):
    field_type = "checkbox"
    multiple = True
    validator = CheckBoxValidator()


class SelectionTable(SelectionField):
    field_type = twc.Param()
    selected_verb = "checked"
    template = "genshi:tw2.forms.templates.selection_table"
    cols = twc.Param('Number of columns', default=1)
    options_rows = twc.Variable()
    grouped_options_rows = twc.Variable()

    def _group_rows(self, seq, size):
        if not hasattr(seq, 'next'):
            seq = iter(seq)
        while True:
            chunk = []
            try:
                for i in xrange(size):
                    chunk.append(seq.next())
                yield chunk
            except StopIteration:
                if chunk:
                    yield chunk
                break

    def prepare(self):
        super(SelectionTable, self).prepare()
        self.options_rows = self._group_rows(self.options, self.cols)
        self.grouped_options_rows = [(g, self._group_rows(o, self.cols)) for g, o in self.grouped_options]


class RadioButtonTable(SelectionTable):
    field_type = 'radio'
    validator = RadioButtonValidator


class CheckBoxTable(SelectionTable):
    field_type = 'checkbox'
    multiple = True
    validator = CheckBoxValidator


#--
# Layout widgets
#--
class BaseLayout(twc.CompoundWidget):
    """
    The following CSS classes are used, on the element containing both a child widget and its label.

    `odd` / `even`
        On alternating rows. The first row is odd.

    `required`
        If the field is a required field.

    `error`
        If the field contains a validation error.
    """

    label = twc.ChildParam('Label for the field. If this is Auto, it is automatically derived from the id. If this is None, it supresses the label.', default=twc.Auto)
    help_text = twc.ChildParam('A longer description of the field', default=None)
    hover_help = twc.Param('Whether to display help text as hover tips', default=False)
    container_attrs = twc.ChildParam('Extra attributes to include in the element containing the widget and its label.', default=None)

    resources = [twc.CSSLink(modname='tw2.forms', filename='static/forms.css')]

    def prepare(self):
        super(BaseLayout, self).prepare()
        for c in self.children:
            if c.label is twc.Auto:
                c.label = twc.util.name2label(c.id_elem) if c.id_elem else ''


class TableLayout(BaseLayout):
    __doc__ = """
    Arrange widgets and labels in a table.
    """ + BaseLayout.__doc__
    template = "genshi:tw2.forms.templates.table_layout"


class ListLayout(BaseLayout):
    __doc__ = """
    Arrange widgets and labels in a list.
    """ + BaseLayout.__doc__
    template = "genshi:tw2.forms.templates.list_layout"


class RowLayout(BaseLayout):
    """
    Arrange widgets in a table row. This is normally only useful as a child to
    :class:`GridLayout`.
    """
    template = "genshi:tw2.forms.templates.row_layout"


class GridLayout(twc.RepeatingWidget):
    """
    Arrange labels and multiple rows of widgets in a grid.
    """
    child = RowLayout
    template = "genshi:tw2.forms.templates.grid_layout"


class Spacer(FormField):
    """
    A blank widget, used to insert a blank row in a layout.
    """
    template = "genshi:tw2.forms.templates.spacer"
    id = None
    label = None


class Label(twc.Widget):
    """
    A textual label. This disables any label that would be displayed by a parent layout.
    """
    template = 'genshi:tw2.forms.templates.label'
    text = twc.Param('Text to appear in label')
    label = None
    id = None


class Form(twc.DisplayOnlyWidget):
    """
    A form, with a submit button. It's common to pass a TableLayout or ListLayout widget as the child.
    """
    template = "genshi:tw2.forms.templates.form"
    action = twc.Param('URL to submit form data to. If this is None, the form submits to the same URL it was displayed on.', default=None, attribute=True)
    method = twc.Param('HTTP method used for form submission.', default='post', attribute=True)
    submit_text = twc.Param('Text for the submit button. If this is None, no submit button is generated.', default='Save')


class FieldSet(twc.DisplayOnlyWidget):
    """
    A field set. It's common to pass a TableLayout or ListLayout widget as the child.
    """
    template = "genshi:tw2.forms.templates.fieldset"
    legend = twc.Param('Text for the legend', default=None)

class TableForm(Form):
    """This is equivalent to a Form containing a TableLayout. children of the TableForm become children of the TableLayout."""
    child = TableLayout

class ListForm(Form):
    """This is equivalent to a Form containing a ListLayout. children of the ListForm become children of the ListLayout."""
    child = ListLayout

class TableFieldSet(FieldSet):
    """This is equivalent to a FieldSet containing a TableLayout. children of the TableFieldSet become children of the TableLayout."""
    child = TableLayout

class ListFieldSet(FieldSet):
    """This is equivalent to a FieldSet containing a ListLayout. children of the ListFieldSet become children of the ListLayout."""
    child = ListLayout



class FormPage(twc.Page):
    """
    A page that contains a form. The :meth:`request` method performs validation,
    redisplaying the form on errors. On success, it calls
    :meth:`validated_request`.
    """

    @classmethod
    def request(cls, req):
        if req.method == 'GET':
            return super(FormPage, cls).request(req)
        elif req.method == 'POST':
            try:
                data = cls.validate(req.POST)
                resp = cls.validated_request(req, data)
            except twc.ValidationError, e:
                resp = webob.Response(request=req, content_type="text/html; charset=UTF8")
                resp.body = e.widget.display().encode('utf-8')
            return resp

    @classmethod
    def validated_request(cls, req, data):
        resp = webob.Response(request=req, content_type="text/html; charset=UTF8")
        resp.body = 'Form posted successfully'
        return resp
