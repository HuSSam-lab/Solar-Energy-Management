import json
from .inverter_script import calculate_avg_of_reading, get_avg, ldr_sensor_calibration, read_ldr_sensor, reset_inverter_parameters, settings_call, settings_post, checkRealData
from . models import Inverter_readings, Commands, User_Settings
from .serializers import DataSerializer, CommandSerializer, SettingSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.utils import dateformat
import datetime

def is_admin_check(user_token):
    token = Token.objects.get(key=user_token)
    user = token.user
    user = User.objects.filter(username = str(user))[0]
    return user

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calibrate_ldr_sensor(request):
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    if user.is_superuser:
        ldr_sensor = ldr_sensor_calibration()
        if (ldr_sensor[0]):
            user_settings = User_Settings.objects.all().last()
            user_settings.min_ldr = ldr_sensor[1]
            user_settings.max_ldr = ldr_sensor[2]
            user_settings.last_edit = dateformat.format(datetime.datetime.now(), 'Y-m-d H:i:s')
            user_settings.save()
            return Response({'Success':True , 'Message' : 'Sensor Calibrated'})
        return Response({'Success':False , 'Message' : 'Sensor Connection Error'})
    return Response({'Success':False , 'Message' : "Permission Denied" })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ldr_sensor_value(request):
    sensor_value = read_ldr_sensor()
    print(sensor_value)
    if (sensor_value != -1):
        return Response({'Success':True , 'Sensor Value' : sensor_value })
    return Response({'Success':False , 'Message' : "Sensor Connection Error" })


#Calculate the projected power using LDR sensor and solar panels
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def projected_power(request):
    settings = User_Settings.objects.all().last()
    min_ldr = settings.min_ldr
    max_ldr = settings.max_ldr
    if (min_ldr == -1 or max_ldr == -1):
        return Response({'Success':False , 'Message' : "Sensor Calibration Error" })
    sensor_value = read_ldr_sensor()
    if (sensor_value == -1):
        return Response({'Success':False , 'Message' : "Sensor Connection Error" })
    if (sensor_value < min_ldr):
        sensor_value = min_ldr
    if (sensor_value > max_ldr):
        sensor_value = max_ldr
    percent = 1 - (sensor_value - min_ldr) / (max_ldr - min_ldr)
    projected_power =  int(percent * settings.solar_panels * settings.single_solar_max_power)
    return Response({'Success':True , 'Projected Power Watt' : projected_power })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_last_readings_avg(request):
    if (checkRealData):
        print(get_avg())
        return Response({'Success':True , 'Message' : [get_avg()]})
    minutes = User_Settings.objects.last().last_readings_avg
    last_object = Inverter_readings.objects.last()
    minutes_ago = last_object.created_at + datetime.timedelta(minutes = -minutes)
    print(minutes_ago)
    data = Inverter_readings.objects.filter(created_at__gte = minutes_ago)
    avg = calculate_avg_of_reading(data)
    return Response({'Success':True , 'Message' : [avg]})
# print("--- %s seconds ---" % (time.time() - start_time))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def data_list_api(request):
    # all_opjects = Inverter_readings.objects.all().latest()
    # for object in all_opjects:
    #     object.created_at = dateformat.format(object.created_at, 'Y-m-d H:i:s')
    #     object.save()
    # data = DataSerializer(all_opjects , many=True).data
    # return Response({'Success':True , 'data List' : data})

#NEW
    last_object = Inverter_readings.objects.last()
    last_object.created_at = dateformat.format(last_object.created_at, 'Y-m-d H:i:s')
    last_object.save()
    data = DataSerializer(last_object).data
    return Response({'Success':True , 'data List' : [data]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def command_list_api(request):
    all_opjects = Commands.objects.all()
    data = CommandSerializer(all_opjects , many=True).data
    return Response({'Success':True , 'command List' : data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_setting(request):
    settings = User_Settings.objects.all().last()
    settings.last_edit = dateformat.format(settings.last_edit, 'Y-m-d H:i:s')
    settings.save()
    data = SettingSerializer([settings] , many=True).data
    return Response({'Success':True , 'User Setting' : data})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_user_setting(request):
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    if user.is_superuser:
        settings = User_Settings.objects.all().last()
        settings.read_time = request.POST.get('read_time')
        settings.last_readings_avg = request.POST.get('last_readings_avg')
        settings.solar_panels = request.POST.get('solar_panels')
        settings.single_solar_max_power = request.POST.get('single_solar_max_power')
        #DELETED BREAKERS
        #settings.breaker_limit = request.POST.get('breaker_limit')
        settings.home_name = request.POST.get('home_name')
        settings.last_edit = dateformat.format(datetime.datetime.now(), 'Y-m-d H:i:s')
        settings.save()
        data = SettingSerializer([settings] , many=True).data
        return Response({'Success':True , 'User Setting' : data})
    return Response({'Success':False , 'Message' : "permission denied" })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inverter_setting_list_api(request):
    #Local Data
    if (not checkRealData()):
        f = open("script_output/settings.json")
        inverter_settings = json.load(f)
        f.close()

    #Real Data
    if (checkRealData()):
        inverter_settings = settings_call()
    
    inverter_settings['max_ac_charging_current'] = str(inverter_settings['max_ac_charging_current'])
    return Response({'Success':True , 'Inverter Settings' : inverter_settings})



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_detail(request):
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    user = User.objects.filter(username = str(user))[0]
    user_dict = {}
    user_dict['username']=user.username
    user_dict['admin']=user.is_superuser
    return Response({'Success':True , 'user detail' : user_dict })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_register(request):
    user = User.objects.filter(is_superuser = False)
    if user:
        return Response({'Success':False , 'Message': 'user exists: {}'.format(user[0].username) })
    user = User()
    user.username=request.POST.get('username', '')
    user.set_password(request.POST.get('password', ''))
    user.save()
    return Response({'Success':True , 'Message' : 'user created: {}'.format(user.username) })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request):
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    if user.is_superuser:
        user_1 = User.objects.filter(is_superuser = False)
        if user_1:
            user_1[0].delete()
            return Response({'Success':True , 'Message' : 'user deleted'})
        return Response({'Success':False , 'Message' : 'user not found' })
    return Response({'Success':False , 'Message' : "permission denied" })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_normal_pass(request):
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    new_pass = request.POST.get('new_password1')
    new_pass_check = request.POST.get('new_password2')
    if new_pass != new_pass_check:
        return Response({'Success':False , 'Message' : "The two password fields didn’t match."})
    if user.is_superuser:
        user_1 = User.objects.filter(is_superuser = False)
        if user_1:
            user_1[0].set_password(new_pass)
            return Response({'Success':True , 'Message' : 'The password for the normal user has been changed'})
        return Response({'Success':False , 'Message' : 'user not found' })
    return Response({'Success':False , 'Message' : "permission denied" })



def generate_commnad(inverter_settings, post_data, post_command, command, key=""):
    temp = ""
    if command.boundries_prefix != "None":
        temp = command.boundries_prefix
    if not key:
        return (command.command_shortcut + temp + str(post_data['Inverter Settings'][post_command]))
    return (command.command_shortcut + temp + str(key))

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_inverter_setting(request):
    #Local Data
    if (not checkRealData()):
        f = open("script_output/settings.json")
        inverter_settings = json.load(f)
        f.close()

    #Real Data
    if (checkRealData()):
        inverter_settings = settings_call()
    
    inverter_settings['max_ac_charging_current'] = str(inverter_settings['max_ac_charging_current'])
    not_found = []
    script_commands = []
    user = is_admin_check(request.headers['Authorization'].split(' ')[1])
    if user.is_superuser:
        post_data = json.loads(request.body)
        for post_command in post_data['Inverter Settings'].keys():
            commands_list = Commands.objects.filter(command_shortcut_in_settings=post_command)
            if commands_list:
                if len(commands_list) > 1:
                    if post_data['Inverter Settings'][post_command] == 'enabled':
                        for c in commands_list:
                            if c.command_shortcut.lower() == 'pe':
                                command = c
                    elif post_data['Inverter Settings'][post_command] == 'disabled':
                        for c in commands_list:
                            if c.command_shortcut.lower() == 'pd':
                                command = c
                else:     
                    command = commands_list[0]
                boundries = command.boundries
                if post_command == 'max_ac_charging_current':
                    post_data['Inverter Settings'][post_command] = str(post_data['Inverter Settings'][post_command])
                
                if type(post_data['Inverter Settings'][post_command]) is not str:
                    min = boundries['min']
                    max = boundries['max']
                    # if min != None and max != None:
                    if (post_data['Inverter Settings'][post_command]<= max) and (post_data['Inverter Settings'][post_command]>=min) and inverter_settings[post_command] != post_data['Inverter Settings'][post_command]:
                        script_commands.append(generate_commnad(inverter_settings, post_data, post_command, command))
                else:
                    post_command_words = post_data['Inverter Settings'][post_command].replace('-', ' ')
                    post_command_words = post_data['Inverter Settings'][post_command].replace('+', 'and').split(' ')
                    post_command_words = [val.lower() for val in post_command_words]
                    choices = boundries['choices']
                    if len(choices) != 0:
                        command_choices_keys = [key for key in choices.keys()]
                        for key in command_choices_keys:
                            if len(post_command_words) >= 2:
                                num_matching_words = 0
                                k = key.replace('-', ' ')
                                k = key.replace('+', 'and')
                                key_list = k.split(' ')
                                if len(key_list) >= 2:
                                    for k_2 in key_list:
                                        if k_2.lower() in post_command_words:
                                            num_matching_words = num_matching_words + 1
                                if num_matching_words >= 2 and inverter_settings[post_command] != post_data['Inverter Settings'][post_command]:
                                    script_commands.append(generate_commnad(inverter_settings, post_data, post_command, command, choices[key]))
                            else:
                                if post_data['Inverter Settings'][post_command].lower() == key.lower() and inverter_settings[post_command] != post_data['Inverter Settings'][post_command]:
                                    script_commands.append(generate_commnad(inverter_settings, post_data, post_command, command, choices[key]))
            else:
                not_found.append(post_command)
        print(script_commands)
        ##########################################################
        if len(script_commands) != 0:
            #Real Data
            if (checkRealData()):
                settings_post(script_commands)
            
            #Local Data
            if (not checkRealData()):
                # get the new settings from request data
                new_settings = json.loads(request.body)
                new_settings = new_settings['Inverter Settings']

            # find the differences and update settings
                for key in new_settings.keys():
                    if key in inverter_settings and inverter_settings[key] != new_settings[key]:
                        inverter_settings[key] = new_settings[key]

        # write back the updated settings
                with open("script_output/settings.json", "w") as f:
                    json.dump(inverter_settings, f)
            
        f = open("script_output/has_not_command_in_settings.json", 'w+')
        # not_found = json.load({'has_not_command_in_settings':not_found})
        json.dump({'has_not_command_in_settings':not_found}, f)
        f.close()

        f = open("script_output/script_command_in_settings.json", 'w+')
        # not_found = json.load({'has_not_command_in_settings':not_found})
        json.dump({'script_command_in_settings':script_commands}, f)
        f.close()
    else:
        return Response({'Success':False , 'Message' : "permission denied" })
    return Response({'Success':True , 'Inverter Settings' : 'inverter_settings'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def freset_inverter_parameters(request):
    id = request.POST.get('inverter_serial_number')
    inverter_serial_number = User_Settings.objects.last().inverter_serial_number
    if int(inverter_serial_number) != int(id):
        return Response({'Success':False , 'Message' : "inverter serial number didn't match" })
    reset_inverter_parameters()
    return Response({'Success':True , 'Message' : "The inverter parameters have been reset successfully" })