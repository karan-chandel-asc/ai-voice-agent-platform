from django.shortcuts import render


def home(request):
    return render(request, 'home.html')

def login_page(request):
    return render(request, 'voice_login.html')

def register_page(request):
    return render(request, 'voice_register.html')

def dashboard(request):
    return render(request, 'voice_dashboard.html')

def agents_list(request):
    return render(request, 'voice_agents.html')

def agent_create(request):
    return render(request, 'voice_agent_create.html')

def agent_detail(request, pk):
    return render(request, 'voice_agent_detail.html', {'pk': pk})

def call_history(request):
    return render(request, 'voice_call_history.html')

def call_detail(request, pk):
    return render(request, 'voice_call_detail.html', {'pk': pk})

def analytics(request):
    return render(request, 'voice_analytics.html')


def integrations(request):
    return render(request, 'voice_integrations.html')

def knowledge_base(request):
    return render(request, 'voice_knowledge_base.html')
