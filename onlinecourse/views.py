from django.db.models.query_utils import Q
from django.shortcuts import render
from django.http import HttpResponseRedirect, request, HttpResponse
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Lesson
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
logging.disable(logging.CRITICAL)
from math import ceil
import uuid
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            print(course)
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        # print("course_list: ============> ",courses)
        return courses

class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super(CourseDetailView, self).get_context_data(**kwargs)
        # print(context['course'].id)
        dummy_lesson = Lesson.objects.filter(course_id = context['course'].id)
        lesson_dummy_id = []

        for l in dummy_lesson:
            lesson_dummy_id.append(l.id)
        # print("Lesson Id ===============> ",lesson_dummy_id)
        # Create any data and add it to the context
        context['question_list'] = Question.objects.filter(lesson_id__in = lesson_dummy_id)
        return context
    

def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    submitted_anwsers  = extract_answers(request)

    dummy_lesson = Lesson.objects.filter(course_id = course_id)
    lesson_dummy_id = []

    for l in dummy_lesson:
        lesson_dummy_id.append(l.id)
    # print("Lesson Id ===============> ",lesson_dummy_id)
    # Create any data and add it to the context
    question_list = Question.objects.filter(lesson_id__in = lesson_dummy_id)
    total_marks = 0
    marks_obtained = 0

    for question in question_list:
        print("Question ===========>" + question.content + "======> marks " + str(question.grade))
        correct_ans = True
        for choice in question.choice_set.all():
            if (choice.id in submitted_anwsers) and (not choice.is_correct):
                correct_ans = False
                break
        if Question.is_get_score(question, submitted_anwsers) and correct_ans:
            marks_obtained+=question.grade

        total_marks+=question.grade

    percent_obtained = int(ceil((marks_obtained/total_marks)*100))
    # return HttpResponse("Success" + str(percent_obatained), content_type='application/json')
    # request.body["percent_obatained"] = percent_obatained
    submission_id = uuid.uuid1()
    print(submission_id)
    context = {}
    context['course_id'] = course_id
    context['percent_obtained'] = percent_obtained
    context['submission_id'] = submission_id
    context['question_list'] = question_list
    context['submitted_anwsers'] = submitted_anwsers
    print("Submitted >>>>>>>>>>>>>>>>>>>>>>>>>>", submitted_anwsers)
    # HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course_id,percent_obtained,submission_id)))
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)

# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_anwsers = []
    print(request.method)
    if request.method == 'GET':
        return redirect('onlinecourse:index')
    try:
        print(request.POST)
        for key in request.POST:
            if key.startswith('choice'):
                value = request.POST[key]
                choice_id = int(value)
                submitted_anwsers.append(choice_id)
    except Exception as err:
        print("Extract Answer error ===============> ", err)
    print("Sbmitted Answers ==================>",submitted_anwsers)
    
    # return HttpResponse(submitted_anwsers, content_type='application/json')
    return submitted_anwsers




# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
# def show_exam_result(request, course_id, submission_id):
#     context = {}
#     context['course_id'] = course_id
#     context['percent_obtained'] = request.body.percent_obatained
#     return render(request, 'onlinecourse/exam_result_bootstrap.html', context)



