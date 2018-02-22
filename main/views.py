from django.views import generic
from django.http import FileResponse
from django.template.defaulttags import register
import imgkit
import operator

from .models import Table, RoomLine, ChamberLine, Building


MONTHS = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 
          'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
ARROW_WIDTH = 16

IMAGE_FILENAME = 'image.png'


@register.filter
def key(dictionary, k):
    return dictionary.get(k)


class TableDetailView(generic.DetailView):
    model = Table
    image = False

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        date = data['table'].date
        data['datecap'] = '{0} {1}'.format(date.day, MONTHS[date.month - 1])

        # Строки передаются отдельно от всего расписания, чтобы разделить их на две категории (chamber / room)
        room_lines = [line for line in data['table'].line_set.select_subclasses() if isinstance(line, RoomLine)]
        room_lines.sort(key=lambda line: line.room.number)
        room_lines.sort(key=lambda line: line.room.floor, reverse=True)
        room_lines.sort(key=lambda line: line.room.building.name)

        chamber_lines = [line for line in data['table'].line_set.select_subclasses() if isinstance(line, ChamberLine)]
        chamber_lines.sort(key=lambda line: line.chamber.values()[0]['name'])

        # links = [(номер_начальной_строки, номер_конечной_строки, направление_назад_или_вперед), ...]
        lines_pk = [line.pk for line in room_lines] + [0] + [line.pk for line in chamber_lines]
        links = [(i, lines_pk.index(line.link.pk)) for i, line in enumerate(room_lines) if line.link]
        links = [(frm, to, False) if frm < to else (to, frm, True) for frm, to in links]
        links.sort(key=operator.itemgetter(0))
        if links:
            classes = link_table(links, len(lines_pk))
            data['comment_indent'] = max(cl[1] for ln in classes for cl in ln)
            # Запись классов для стрелочек в строки расписания
            for i, cls in enumerate(classes):
                if i < len(room_lines):
                    room_lines[i].cls = cls
                elif i == len(room_lines):
                    data['blank_cls'] = cls
                elif i > len(room_lines):
                    chamber_lines[i - len(room_lines) - 1].cls = cls

        data['room_lines'] = room_lines
        data['chamber_lines'] = chamber_lines
        data['buildings'] = Building.objects.all()
        data['column_types'] = data['table'].column_types()
        data['image'] = self.image

        return data


def link_table(links, total):
    # поиск свободного места для стрелочки (чтобы они не накладывались)
    cols = []
    for link_from, link_to, rev in links:
        free_col = 1
        for j, (col, frm, to, _) in enumerate(cols):
            if link_from < to <= link_to:
                free_col = max(free_col, col + 1)
            elif frm < link_from and link_to < to and col == free_col:
                free_col = col
                cols[j][0] = col + 1
        cols.append([free_col, link_from, link_to, rev])

    # преобразование полученного в css-классы и ширину (вынос) стрелочки
    classes = [[] for i in range(total)]
    for col, frm, to, rev in cols:
        classes[frm].append(('out', col * ARROW_WIDTH))
        for i in range(frm + 1, to):
            classes[i].append(('down', col * ARROW_WIDTH))
        classes[to].append(('in', col * ARROW_WIDTH))
        if rev:
            classes[frm].append(('arrow back', 0))
        else:
            classes[to].append(('arrow forw', 0))
    return classes


def table_image(request, pk):
    html_response = TableDetailView.as_view(image=True)(request, pk=pk)
    table_date = html_response.context_data['table'].date
    html_response.render()
    content = str(html_response.content, 'utf-8')
    imgkit.from_string(content, IMAGE_FILENAME)
    response = FileResponse(open(IMAGE_FILENAME, 'rb'))
    response['Content-Disposition'] = 'attachment; filename=table-{0}.png'.format(table_date.strftime('%Y-%m-%d'))
    return response

