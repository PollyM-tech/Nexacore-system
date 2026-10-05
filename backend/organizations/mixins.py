from .services import get_user_organization


class OrganizationQuerySetMixin:
    organization_field = "organization"

    def get_organization(self):
        return get_user_organization(self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            **{self.organization_field: self.get_organization()}
        )

    def perform_create(self, serializer):
        serializer.save(
            **{self.organization_field: self.get_organization()}
        )