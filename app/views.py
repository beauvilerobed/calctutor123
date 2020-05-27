from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render_to_response, redirect, render
from django.template.loader import render_to_string
from django import forms
from django.views.generic.base import TemplateView
from django.views.generic import View
import django

from chat import chatbot_response

import sympy
from logic.utils import Eval
from logic.logic import Evaluate_card, mathjax_latex
from logic.resultsets import get_card, find_result_set

from mathtutor import settings

import os
import json
import urllib
# https://docs.python.org/3/library/urllib.parse.html#module-urllib.parse
import urllib.parse
import datetime
import traceback

from django.views.decorators.csrf import csrf_exempt
# https://devcenter.heroku.com/articles/getting-started-with-python#push-local-changes
import requests

EXAMPLES = [
    ('Calculus', [
        ['Derivatives', [
            ('Learn how to derive the product rule for multiple functions', 'diff(f(x)*g(x)*h(x)*k(x))'),
            ('Learn how to derive the  the quotient rule', 'diff(f(x)/g(x))'),
            ('Learn how to use power rule and Chain rule', 'diff(cos(x)^7, x)'),
            ('See the steps for derivatives of this function', 'diff(x^4 / (1 + (tan(sin(x))))^2)'),
            ('Learn multiple ways to derive functions', 'diff(cot(y), y)'),
            ('Learn to differentiate implicitly', 'diff(z*x^4 - tan(z), z)'),

        ]],
        ['Antiderivatives', [
            ('Learn how to integrate this function','integrate(cot(x))'),
            ('Learn how to integrate multiple variables', 'integrate(x^100 + x, x)'),
            ('Learn common integrals', 'integrate(1/z, z)'),
            ('Learn steps for these integrals', 'integrate(exp(2x) / (1 + exp(x)), x)'),
            'integrate(1 /(x^2-x-2),x)',
            'integrate((2+3/x)**2)',
            ('And if we don\'t know, we will let you know' , 'integrate(1/sqrt(x^2+1), x)'),
        ]],
    ]),
]

# https://devcenter.heroku.com/articles/getting-started-with-python#push-local-changes
def index(request):
    r = requests.get('http://httpbin.org/status/418')
    print(r.text)
    return HttpResponse('<pre>' + r.text + '</pre>')

class MobileTextInput(forms.widgets.TextInput):
    # https://stackoverflow.com/questions/52039654/django-typeerror-render-got-an-unexpected-keyword-argument-renderer
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs['autocorrect'] = 'off'
        attrs['autocapitalize'] = 'off'
        return super(MobileTextInput, self).render(name, value, attrs)

class SearchForm(forms.Form):
    i = forms.CharField(required=False, widget=MobileTextInput())

def authenticate(view):
    def _wrapper(request, **kwargs):
        user = None
        result = view(request, user, **kwargs)

        try:
            template, params = result
        except ValueError:
            return result

        if user:
            params['auth_url'] = None
            params['auth_message'] = None
        else:
            params['auth_url'] = None
            params['auth_message'] = None
        return template, params
    return _wrapper

@authenticate
def index(request, user):
    form = SearchForm()
    user = None

    history = None

    return render(request,"index.html", {
        "form": form,
        "MEDIA_URL": settings.STATIC_URL,
        "examples": EXAMPLES
        })

@authenticate
def table(request, user):
    return render(request,"table.html", {
        "MEDIA_URL": settings.STATIC_URL,
        "table_active": "selected",
        })

@authenticate
def input(request, user):
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            input = form.cleaned_data["i"]

            g = Evaluate_card()
            r = g.eval(input)

            if not r:
                r = [{
                    "title": "Input",
                    "input": input,
                    "output": "Can't handle the input."
                }]
            # else:
            #     r = [{
            #         "title": "Input",
            #         "input": str(r[1]),
            #         "output": "Can't handle the input."
            #     }]

            return render(request,"result.html", {
                "input": input,
                "result": r,
                "form": form,
                "MEDIA_URL": settings.STATIC_URL,
                })

def _process_card(request, card_name):
    variable = request.GET.get('variable')
    expression = request.GET.get('expression')
    if not variable or not expression:
        raise Http404
# https://stackoverflow.com/questions/8628152/url-decode-with-python-3/8628164
    variable = urllib.parse.unquote(variable)
    expression = urllib.parse.unquote(expression)

    g = Evaluate_card()

    parameters = {}
    for key, val in request.GET.items():
        parameters[key] = ''.join(val)

    return g, variable, expression, parameters


def eval_card(request, card_name):
    g, variable, expression, parameters = _process_card(request, card_name)

    try:
        result = g.eval_card(card_name, expression, variable, parameters)
    except ValueError as e:
        return HttpResponse(json.dumps({
            'error': e.message
        }), content_type="application/json")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(json.dumps({
            'error': ('There was an error in Gamma. For reference'
                      'the last five traceback entries are: ' + trace)
        }), content_type="application/json")

    return HttpResponse(json.dumps(result), content_type="application/json")

def get_card_info(request, card_name):
    g, variable, expression, _ = _process_card(request, card_name)

    try:
        result = g.get_card_info(card_name, expression, variable)
    except ValueError as e:
        return HttpResponse(json.dumps({
            'error': e.message
        }), content_type="application/json")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(json.dumps({
            'error': ('There was an error in Gamma. For reference'
                      'the last five traceback entries are: ' + trace)
        }), content_type="application/json")
# https://github.com/crucialfelix/django-ajax-selects/pull/82/files
    return HttpResponse(json.dumps(result), content_type="application/json")

def get_card_full(request, card_name):
    g, variable, expression, parameters = _process_card(request, card_name)

    try:
        card_info = g.get_card_info(card_name, expression, variable)
        result = g.eval_card(card_name, expression, variable, parameters)
        card_info['card'] = card_name
        card_info['cell_output'] = result['output']

        html = render_to_string('card.html', {
            'cell': card_info,
            'input': expression
        })
    except ValueError as e:
        card_info = g.get_card_info(card_name, expression, variable)
        return HttpResponse(render_to_string('card.html', {
            'cell': {
                'title': card_info['title'],
                'input': card_info['input'],
                'card': card_name,
                'variable': variable,
                'error': e.message
            },
            'input': expression
        }), content_type="text/html")
    except:
        trace = traceback.format_exc(5)
        return HttpResponse(render_to_string('card.html', {
            'cell': {
                'card': card_name,
                'variable': variable,
                'error': trace
            },
            'input': expression
        }), content_type="text/html")

    response = HttpResponse(html, content_type="text/html")
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'

    return response

class ChatBotAppView(TemplateView):
    template_name = 'app.html'


class ChatBotApiView(View):

    """
    Provide an API endpoint to interact with ChatterBot.
    """

    def post(self, request, *args, **kwargs):
        """
        Return a response to the statement in the posted data.

        * The JSON data should contain a 'text' attribute.
        """


        input_data = json.loads(request.body.decode('utf-8'))  
        msg = input_data['text']
        
        response = chatbot_response(msg)

        return JsonResponse({
            'text': [
                response
            ]
        }, status=200)

def handler404(request, exception):
    return render(request,"404.html")

def handler500(request):
    return render(request,"500.html")