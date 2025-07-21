from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Interview
from .serializers import InterviewCreateSerializer, InterviewListSerializer

# Create your views here.

class InterviewCreateView(generics.CreateAPIView):
    """创建面试接口"""
    queryset = Interview.objects.all()
    serializer_class = InterviewCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = serializer.save()
        return Response({
            'id': interview.id,
            'interview_time': interview.interview_time,
            'position_name': interview.position_name,
            'company_name': interview.company_name,
            'position_type': interview.position_type,
            'msg': '面试创建成功'
        }, status=status.HTTP_201_CREATED)


class InterviewListView(generics.ListAPIView):
    """获取用户面试列表接口"""
    serializer_class = InterviewListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的面试记录"""
        return Interview.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'interviews': serializer.data,
            'total': queryset.count()
        }, status=status.HTTP_200_OK)
