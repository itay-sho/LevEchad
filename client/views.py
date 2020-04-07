import io
from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.contrib.staticfiles import finders

from .forms import *
from .models import Volunteer, City, Language, VolunteerSchedule, VolunteerCertificate, HelpRequest, Area


def thanks(request):
    try:
        username = request.GET['username']
        pk = request.GET['pk']

        hr = HelpRequest.objects.get(pk=pk, full_name=username)

        return render(request, 'thanks.html', {
            "id": pk,
            "message": "סטאטוס הבקשה שלך בLIVE",
            "status": str(hr.get_status_display())

        })
    except Exception as e:
        return render(request, 'thanks.html', {
            "id": " ",
            "message": "התקשר למוקד שלנו לפרטים נוספים",
            "status": ""
        })


def thanks_volunteer(request):
    volunteer_id = request.GET['vol_id']
    volunteer = Volunteer.objects.get(id=volunteer_id)
    volunteer_certificate = volunteer.get_active_certificates().first()

    return render(request, 'thanks_volunteer.html', {
        "name": f'{volunteer.first_name} {volunteer.last_name}',
        "certificate": volunteer_certificate
    })


def homepage(request):
    context = {
        "numbers": {
            "total_volunteers": Volunteer.objects.count() + 1786,
            "total_help_requests": HelpRequest.objects.count() + 84     #added 1786 and 84 since those are the stats for before this app

        }
    }

    return render(request, 'index.html', context)


def get_help(request):
    return render(request, 'get_help.html', {})


def volunteer_view(request):
    # if this is a POST request we need to process the form data
    organization = request.GET.get('org', '')
    if request.method == 'POST':
        form = VolunteerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data
            languages = Language.objects.filter(name__in=answer["languages"])
            areas = Area.objects.filter(name__in=answer["area"])

            volunteer_new = Volunteer.objects.create(
                tz_number=answer["id_number"],
                first_name=answer["first_name"],
                last_name=answer["last_name"],
                email=answer["email"],
                date_of_birth=answer["date_of_birth"],
                organization=answer['organization'],
                phone_number=answer["phone_number"],
                city=City.objects.get(name=answer["city"]),
                neighborhood=answer['neighborhood'],
                address=answer["address"],
                available_saturday=answer["available_on_saturday"],
                notes=answer["notes"],
                moving_way=answer["transportation"],
                hearing_way=answer["hearing_way"],
                keep_mandatory_worker_children=(answer["childrens"] == "YES"),
                guiding=False
            )
            volunteer_new.languages.set(languages)
            volunteer_new.areas.set(areas)

            # creating volunteer certificate
            volunteer_new.get_or_generate_valid_certificate()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            # TODO Don't hardcode URLs, get them by view
            return HttpResponseRedirect('/client/schedule?vol_id=' + str(volunteer_new.pk))
    # if a GET (or any other method) we'll create a blank form
    else:
        form = VolunteerForm(initial={'organization': organization})

    return render(request, 'volunteer.html', {'form': form, 'organization': organization})


def schedule(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            new_schedule = VolunteerSchedule(Sunday="".join(answer["sunday"]), Monday="".join(answer["monday"]),
                                             Tuesday="".join(answer["tuesday"]), Wednesday="".join(answer["wednesday"]),
                                             Thursday="".join(answer["thursday"]), Friday="".join(answer["friday"]),
                                             Saturday="".join(answer["saturday"]))
            volunteerSchedule = Volunteer.objects.get(id=int(request.POST.get('vol_id', '')))
            new_schedule.save()
            volunteerSchedule.schedule = new_schedule
            volunteerSchedule.save()
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            vol_pk = request.POST['vol_id']

            return HttpResponseRedirect('/client/thanks_volunteer?vol_id=' + str(vol_pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ScheduleForm()

    return render(request, 'schedule.html', {'form': form, 'id': request.GET.get('vol_id', '')})


def shopping_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ShoppingForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            areasGot = Area.objects.all().get(name=answer["area"])

            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="BUYIN",
                                      type_text=answer["to_buy"], area=areasGot)
            new_request.save()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:y
            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = ShoppingForm()

    return render(request, 'help_pages/shopping.html', {'form': form})


def find_certificate_view(request):
    context = {'form': GetCertificateForm()}
    if request.method == 'POST':
        form = GetCertificateForm(request.POST)
        if form.is_valid():
            # TODO: change to 'get' instead of 'first' after fixing #50
            volunteer = Volunteer.objects.filter(tz_number=form['id_number'].data).first()
            if volunteer is not None:
                '''
                 TODO: this a hotfix that generate a valid certificate to any user that requests one. 
                 it should be reverted to the commented part  when #52 is solved
                '''
                # active_certificate = volunteer.get_active_certificates().first()
                active_certificate = volunteer.get_or_generate_valid_certificate()

                if active_certificate is not None:
                    context['certificate'] = active_certificate
                else:
                    context['error'] = 'לא נמצאה תעודה בתוקף!'
            else:
                context['error'] = 'מתנדב לא נמצא!'
        else:
            context['error'] = 'יש למלא את השדות כנדרש!'

    return render(request, 'find_certificate.html', context=context)


def download_certificate_view(request, pk):
    # We could've easily used the download attribute on <a> tags w/ the media URL directly,
    # but this doesn't work on Firefox for some reason.
    # This is only for development purposes - see VolunteerCertificate.image_download_url
    with open(VolunteerCertificate.objects.get(id=pk).image.path, 'rb') as image_file:
        response = HttpResponse(image_file.read(), content_type='image/png')
        response['Content-Disposition'] = 'attachment; filename="{}.png"'.format(pk)
        return response


def medic_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = MedicForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            type_text = ""
            if (answer["need_prescription"]):
                type_text = "תרופת מרשם\n"

            areasGot = Area.objects.all().get(name=answer["area"])
            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="MEDICI",
                                      type_text=type_text + answer["medic_name"], area=areasGot)
            new_request.save()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:y
            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MedicForm()

    return render(request, 'help_pages/medic.html', {'form': form})


def other_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = OtherForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            areasGot = Area.objects.all().get(name=answer["area"])
            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="OTHER",
                                      type_text=answer["other_need"], area=areasGot)
            new_request.save()

            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = OtherForm()

    return render(request, 'help_pages/other.html', {'form': form})


def travel_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = TravelForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            areasGot = Area.objects.all().get(name=answer["area"])

            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="TRAVEL",
                                      type_text=answer["travel_need"], area=areasGot)
            new_request.save()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:y
            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = TravelForm()

    return render(request, 'help_pages/travel.html', {'form': form})


def phone_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = BaseHelpForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            areasGot = Area.objects.all().get(name=answer["area"])

            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="PHONE_HEL",
                                      type_text="", area=areasGot)
            new_request.save()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:y
            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = BaseHelpForm()

    return render(request, 'help_pages/phone.html', {'form': form})


def workers_help(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = WorkersForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            answer = form.cleaned_data
            areasGot = Area.objects.all().get(name=answer["area"])

            new_request = HelpRequest(full_name=answer["full_name"], phone_number=answer["phone_number"],
                                      city=City.objects.get(name=answer["city"]),
                                      address=answer["address"], notes=answer["notes"], type="WORKERS_HELP",
                                      type_text="", area=areasGot)
            new_request.save()

            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:y
            return HttpResponseRedirect('/client/thanks?username=' + answer["full_name"] + "&pk=" + str(new_request.pk))

    # if a GET (or any other method) we'll create a blank form
    else:
        form = WorkersForm()

    return render(request, 'help_pages/workers.html', {'form': form})
