from constants import PAGE_FORMATS

class Page:

    def __init__(self, page_format='A4', orientation='portrait'):
        # Page setup
        try :
            dims = PAGE_FORMATS[page_format]
        except KeyError:
            raise ValueError('Invalid page format')

        if orientation not in ('portrait', 'landscape'):
            raise ValueError('Invalid orientation')
        else:
            if orientation == 'portrait':
                self._width, self._height = dims
            elif orientation == 'landscape':
                self._width, self._height = dims[1], dims[0]

        self._margins = (10, 10, 10, 10) # top, right, bottom, left

        # Cell dimensions in mm
        self._dot_spc = 2.50
        self._cell_spc = 6.00
        self._line_spc = 10.00

        self.max_cells_per_line = int((self._width - self.margins[1] - self.margins[3]) / self._cell_spc)
        self.max_lines_per_page = int((self._height - self.margins[0] - self.margins[2]) / self._line_spc)



    def write(self):

    @property
    def margins(self):
        return self._margins

    @margins.setter
    def margins(self, values):
        self._margins = values
